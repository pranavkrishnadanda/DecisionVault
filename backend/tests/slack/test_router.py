import hashlib
import hmac
import json
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings

from api.models import Organization, OrganizationMembership, OrganizationRole
from app.slack.encryption import encrypt_token
from app.slack.models import SlackAuditLog, SlackIntegration, SlackIntegrationTestLog


@pytest.fixture
def auth_client(client):
    user_model = get_user_model()
    user = user_model.objects.create_user(
        username="slack-user",
        email="slack@example.com",
        password="pass12345",
    )
    org = Organization.objects.create(name="Slack Org")
    OrganizationMembership.objects.create(
        user=user,
        organization=org,
        role=OrganizationRole.ADMIN,
    )
    client.force_login(user)
    return client, user, org


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "slack-tests",
        }
    },
    SLACK_CLIENT_ID="client-123",
    SLACK_REDIRECT_BASE_URL="https://example.ngrok-free.app",
)
@pytest.mark.django_db
def test_install_redirect(auth_client):
    client, _user, _org = auth_client

    response = client.get("/api/slack/install")

    assert response.status_code == 302
    location = response["Location"]
    assert "https://slack.com/oauth/v2/authorize" in location

    parsed = urlparse(location)
    query = parse_qs(parsed.query)
    assert query["client_id"][0] == "client-123"
    assert "channels:read" in query["scope"][0]
    assert "state" in query

    state = query["state"][0]
    assert cache.get(f"slack_oauth_state:{state}") is not None


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "slack-tests",
        }
    },
    SLACK_CLIENT_ID="client-123",
    SLACK_CLIENT_SECRET="secret-123",
    TOKEN_ENCRYPTION_KEY="S6WwX9_V7yYJfWmQAzB5JjSN1aP5nH-2Wf47p9VWYf8=",
    SLACK_REDIRECT_BASE_URL="https://example.ngrok-free.app",
)
@pytest.mark.django_db
def test_callback_success(auth_client):
    client, user, _org = auth_client
    state = "state-ok"
    cache.set(f"slack_oauth_state:{state}", {"user_id": str(user.id)}, timeout=600)

    with patch("app.slack.router.httpx.post") as mock_post:
        mock_post.return_value.json.return_value = {
            "ok": True,
            "access_token": "xoxb-plaintext-token",
            "team": {"id": "T1", "name": "Workspace 1"},
            "bot_user_id": "B1",
        }
        mock_post.return_value.status_code = 200

        response = client.get(f"/api/slack/callback?code=abc&state={state}")

    assert response.status_code == 302
    assert response["Location"].endswith("/integrations/slack?status=success")
    integration = SlackIntegration.objects.get(team_id="T1")
    assert integration.encrypted_token != "xoxb-plaintext-token"
    assert integration.installed_by_id == user.id

    audit = SlackAuditLog.objects.filter(action=SlackAuditLog.Action.INSTALL).first()
    assert audit is not None
    assert "xoxb" not in json.dumps(audit.details)


@pytest.mark.django_db
def test_callback_invalid_state(auth_client):
    client, _user, _org = auth_client

    response = client.get("/api/slack/callback?code=abc&state=wrong")

    assert response.status_code == 302
    assert "status=error" in response["Location"]
    assert "reason=invalid_state" in response["Location"]
    assert SlackIntegration.objects.count() == 0


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "slack-tests",
        }
    },
    SLACK_CLIENT_ID="client-123",
    SLACK_CLIENT_SECRET="secret-123",
    TOKEN_ENCRYPTION_KEY="S6WwX9_V7yYJfWmQAzB5JjSN1aP5nH-2Wf47p9VWYf8=",
    SLACK_REDIRECT_BASE_URL="https://example.ngrok-free.app",
)
@pytest.mark.django_db
def test_callback_slack_error(auth_client):
    client, user, _org = auth_client
    state = "state-error"
    cache.set(f"slack_oauth_state:{state}", {"user_id": str(user.id)}, timeout=600)

    with patch("app.slack.router.httpx.post") as mock_post:
        mock_post.return_value.json.return_value = {
            "ok": False,
            "error": "invalid_code",
        }
        mock_post.return_value.status_code = 200

        response = client.get(f"/api/slack/callback?code=abc&state={state}")

    assert response.status_code == 302
    assert "reason=invalid_code" in response["Location"]
    assert SlackIntegration.objects.count() == 0


@override_settings(TOKEN_ENCRYPTION_KEY="S6WwX9_V7yYJfWmQAzB5JjSN1aP5nH-2Wf47p9VWYf8=")
@pytest.mark.django_db
def test_channels_list(auth_client):
    client, user, org = auth_client
    integration = SlackIntegration.objects.create(
        org=org,
        team_id="T1",
        team_name="Workspace",
        encrypted_token=encrypt_token("xoxb-token"),
        bot_user_id="B1",
        installed_by=user,
    )

    with patch("app.slack.router.SlackClient.list_channels") as list_channels:
        list_channels.return_value = [
            {
                "id": "C1",
                "name": "general",
                "is_private": False,
                "num_members": 10,
                "topic": "topic",
            }
        ]

        response = client.get(f"/api/slack/channels?integration_id={integration.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["id"] == "C1"


@override_settings(TOKEN_ENCRYPTION_KEY="S6WwX9_V7yYJfWmQAzB5JjSN1aP5nH-2Wf47p9VWYf8=")
@pytest.mark.django_db
def test_channels_unauthorized(client, django_user_model):
    owner = django_user_model.objects.create_user("owner", password="pass12345")
    outsider = django_user_model.objects.create_user("outsider", password="pass12345")
    org = Organization.objects.create(name="OrgX")
    other_org = Organization.objects.create(name="OrgY")
    OrganizationMembership.objects.create(
        user=owner, organization=org, role=OrganizationRole.ADMIN
    )
    OrganizationMembership.objects.create(
        user=outsider, organization=other_org, role=OrganizationRole.ADMIN
    )

    integration = SlackIntegration.objects.create(
        org=org,
        team_id="T1",
        team_name="Workspace",
        encrypted_token=encrypt_token("xoxb-token"),
        bot_user_id="B1",
        installed_by=owner,
    )

    client.force_login(outsider)
    response = client.get(f"/api/slack/channels?integration_id={integration.id}")

    assert response.status_code == 403


@override_settings(TOKEN_ENCRYPTION_KEY="S6WwX9_V7yYJfWmQAzB5JjSN1aP5nH-2Wf47p9VWYf8=")
@pytest.mark.django_db
def test_messages_fetch(auth_client):
    client, user, org = auth_client
    integration = SlackIntegration.objects.create(
        org=org,
        team_id="T1",
        team_name="Workspace",
        encrypted_token=encrypt_token("xoxb-token"),
        bot_user_id="B1",
        installed_by=user,
    )

    with (
        patch("app.slack.router.SlackClient.get_messages") as get_messages,
        patch("app.slack.router.SlackClient.get_replies") as get_replies,
        patch("app.slack.router.SlackClient.get_user") as get_user,
    ):
        get_messages.return_value = {
            "messages": [
                {"user": "U1", "text": "Hello", "ts": "123", "thread_ts": "123"}
            ],
            "has_more": False,
            "next_cursor": "",
        }
        get_replies.return_value = [{"user": "U2", "text": "Reply", "ts": "124"}]
        get_user.side_effect = lambda uid: {
            "display_name": "Alice" if uid == "U1" else "Bob"
        }

        response = client.get(
            f"/api/slack/messages?integration_id={integration.id}&channel_id=C1&limit=100"
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["messages"][0]["user_name"] == "Alice"
    assert payload["messages"][0]["thread_replies"][0]["user_name"] == "Bob"


@override_settings(TOKEN_ENCRYPTION_KEY="S6WwX9_V7yYJfWmQAzB5JjSN1aP5nH-2Wf47p9VWYf8=")
@pytest.mark.django_db
def test_messages_pagination(auth_client):
    client, user, org = auth_client
    integration = SlackIntegration.objects.create(
        org=org,
        team_id="T1",
        team_name="Workspace",
        encrypted_token=encrypt_token("xoxb-token"),
        bot_user_id="B1",
        installed_by=user,
    )

    with (
        patch("app.slack.router.SlackClient.get_messages") as get_messages,
        patch("app.slack.router.SlackClient.get_user") as get_user,
    ):
        get_messages.return_value = {
            "messages": [{"user": "U1", "text": "Hello", "ts": "123"}],
            "has_more": True,
            "next_cursor": "cursor-2",
        }
        get_user.return_value = {"display_name": "Alice"}

        response = client.get(
            f"/api/slack/messages?integration_id={integration.id}&channel_id=C1&limit=100"
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["has_more"] is True
    assert payload["next_cursor"] == "cursor-2"


@override_settings(TOKEN_ENCRYPTION_KEY="S6WwX9_V7yYJfWmQAzB5JjSN1aP5nH-2Wf47p9VWYf8=")
@pytest.mark.django_db
def test_test_message(auth_client):
    client, user, org = auth_client
    integration = SlackIntegration.objects.create(
        org=org,
        team_id="T1",
        team_name="Workspace",
        encrypted_token=encrypt_token("xoxb-token"),
        bot_user_id="B1",
        installed_by=user,
    )

    with patch("app.slack.router.SlackClient.send_message") as send_message:
        send_message.return_value = {"ok": True, "ts": "171.22"}
        response = client.post(
            "/api/slack/test",
            data=json.dumps(
                {"integration_id": str(integration.id), "channel_id": "C1"}
            ),
            content_type="application/json",
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["message_ts"] == "171.22"
    assert SlackIntegrationTestLog.objects.filter(
        integration=integration, success=True
    ).exists()


@override_settings(TOKEN_ENCRYPTION_KEY="S6WwX9_V7yYJfWmQAzB5JjSN1aP5nH-2Wf47p9VWYf8=")
@pytest.mark.django_db
def test_test_message_failure(auth_client):
    client, user, org = auth_client
    integration = SlackIntegration.objects.create(
        org=org,
        team_id="T1",
        team_name="Workspace",
        encrypted_token=encrypt_token("xoxb-token"),
        bot_user_id="B1",
        installed_by=user,
    )

    with patch("app.slack.router.SlackClient.send_message") as send_message:
        send_message.return_value = {"ok": False, "error": "channel_not_found"}
        response = client.post(
            "/api/slack/test",
            data=json.dumps(
                {"integration_id": str(integration.id), "channel_id": "C1"}
            ),
            content_type="application/json",
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"] == "channel_not_found"
    assert SlackIntegrationTestLog.objects.filter(
        integration=integration, success=False
    ).exists()


@override_settings(SLACK_SIGNING_SECRET="signing-secret")
@pytest.mark.django_db
def test_event_verification(auth_client):
    client, _user, _org = auth_client

    body = json.dumps({"type": "url_verification", "challenge": "abc123"})
    timestamp = "1710000000"
    base = f"v0:{timestamp}:{body}".encode()
    signature = "v0=" + hmac.new(b"signing-secret", base, hashlib.sha256).hexdigest()

    response = client.post(
        "/api/slack/events",
        data=body,
        content_type="application/json",
        HTTP_X_SLACK_REQUEST_TIMESTAMP=timestamp,
        HTTP_X_SLACK_SIGNATURE=signature,
    )

    assert response.status_code == 200
    assert response.json() == {"challenge": "abc123"}


@override_settings(SLACK_SIGNING_SECRET="signing-secret")
@pytest.mark.django_db
def test_event_verification_invalid_signature(auth_client):
    client, _user, _org = auth_client

    response = client.post(
        "/api/slack/events",
        data=json.dumps({"type": "event_callback"}),
        content_type="application/json",
        HTTP_X_SLACK_REQUEST_TIMESTAMP="1710000000",
        HTTP_X_SLACK_SIGNATURE="v0=invalid",
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_audit_logging(auth_client):
    client, _user, _org = auth_client

    client.get("/api/slack/install")

    audit = SlackAuditLog.objects.order_by("-timestamp").first()
    assert audit is not None
    assert audit.action == SlackAuditLog.Action.INSTALL_INIT
    serialized = json.dumps(audit.details)
    assert "access_token" not in serialized
    assert "xoxb" not in serialized
