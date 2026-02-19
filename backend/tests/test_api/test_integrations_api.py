from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from api.models import (
    Integration,
    IntegrationDelivery,
    IntegrationDeliveryAttempt,
    Organization,
    OrganizationMembership,
    OrganizationRole,
)
from api.services.credentials_vault import decrypt_credentials, encrypt_credentials


@pytest.fixture
def org_a(db):
    return Organization.objects.create(name="Integration Org A")


@pytest.fixture
def org_b(db):
    return Organization.objects.create(name="Integration Org B")


@pytest.fixture
def admin_a(django_user_model, org_a):
    user = django_user_model.objects.create_user(
        username="integration-admin-a",
        email="integration-admin-a@example.com",
        password="pass1234",
    )
    OrganizationMembership.objects.filter(user=user).delete()
    OrganizationMembership.objects.create(
        user=user,
        organization=org_a,
        role=OrganizationRole.ADMIN,
    )
    return user


@pytest.fixture
def viewer_a(django_user_model, org_a):
    user = django_user_model.objects.create_user(
        username="integration-viewer-a",
        email="integration-viewer-a@example.com",
        password="pass1234",
    )
    OrganizationMembership.objects.filter(user=user).delete()
    OrganizationMembership.objects.create(
        user=user,
        organization=org_a,
        role=OrganizationRole.VIEWER,
    )
    return user


@pytest.fixture
def operator_b(django_user_model, org_b):
    user = django_user_model.objects.create_user(
        username="integration-operator-b",
        email="integration-operator-b@example.com",
        password="pass1234",
    )
    OrganizationMembership.objects.filter(user=user).delete()
    OrganizationMembership.objects.create(
        user=user,
        organization=org_b,
        role=OrganizationRole.OPERATOR,
    )
    return user


@pytest.fixture
def admin_a_client(admin_a):
    client = APIClient()
    client.force_authenticate(user=admin_a)
    return client


@pytest.fixture
def viewer_a_client(viewer_a):
    client = APIClient()
    client.force_authenticate(user=viewer_a)
    return client


@pytest.fixture
def anonymous_client():
    return APIClient()


@pytest.mark.django_db
class TestIntegrationAPI:
    def test_auth_required_for_list(self, anonymous_client):
        response = anonymous_client.get("/api/v1/integrations/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_slack_connector_encrypts_credentials(self, admin_a_client):
        response = admin_a_client.post(
            "/api/v1/integrations/",
            {
                "name": "Primary Slack",
                "connector_type": "slack",
                "config": {
                    "channel_id": "C12345",
                    "message_template": "{{event_type}}: {{payload.decision_id}}",
                },
                "credentials": {
                    "access_token": "xoxb-secret",
                    "refresh_token": "refresh-secret",
                },
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        payload = response.json()
        assert payload["connector_type"] == "slack"
        assert "credentials" not in payload

        integration = Integration.objects.get(id=payload["id"])
        assert integration.credentials_encrypted
        assert integration.credentials_encrypted != "xoxb-secret"

        credentials = decrypt_credentials(integration.credentials_encrypted)
        assert credentials["access_token"] == "xoxb-secret"

    def test_viewer_cannot_create_connector(self, viewer_a_client):
        response = viewer_a_client.post(
            "/api/v1/integrations/",
            {
                "name": "Viewer Slack",
                "connector_type": "slack",
                "config": {"channel_id": "C1"},
                "credentials": {"access_token": "xoxb-secret"},
            },
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cross_org_retrieve_returns_404(self, admin_a_client, operator_b, org_b):
        integration = Integration.objects.create(
            organization=org_b,
            created_by=operator_b,
            name="Other Org Teams",
            connector_type=Integration.ConnectorType.TEAMS,
            config={"channel": "Ops"},
            credentials_encrypted="cipher",
        )

        response = admin_a_client.get(f"/api/v1/integrations/{integration.id}/")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_slack_install_url_contains_signed_state(
        self, admin_a_client, admin_a, org_a
    ):
        integration = Integration.objects.create(
            organization=org_a,
            created_by=admin_a,
            name="Slack OAuth",
            connector_type=Integration.ConnectorType.SLACK,
            config={"channel_id": "COPS"},
            credentials_encrypted=encrypt_credentials({}),
        )

        response = admin_a_client.get(
            f"/api/v1/integrations/{integration.id}/slack/install-url/",
            {"redirect_uri": "https://app.localhost/oauth/slack/callback"},
        )

        assert response.status_code == status.HTTP_200_OK
        install_url = response.json()["install_url"]
        parsed = urlparse(install_url)
        query = parse_qs(parsed.query)
        assert parsed.netloc == "slack.com"
        assert parsed.path == "/oauth/v2/authorize"
        assert "state" in query
        assert query["client_id"][0]

    def test_slack_oauth_callback_updates_tokens(self, admin_a_client, admin_a, org_a):
        integration = Integration.objects.create(
            organization=org_a,
            created_by=admin_a,
            name="Slack OAuth",
            connector_type=Integration.ConnectorType.SLACK,
            config={"channel_id": "COPS"},
            credentials_encrypted=encrypt_credentials({}),
        )

        with patch("api.views.exchange_slack_oauth_code") as mock_exchange:
            mock_exchange.return_value = {
                "access_token": "xoxb-new",
                "refresh_token": "refresh-new",
                "expires_in": 3600,
            }
            response = admin_a_client.post(
                f"/api/v1/integrations/{integration.id}/slack/oauth-callback/",
                {
                    "code": "oauth-code",
                    "redirect_uri": "https://app.localhost/oauth/slack/callback",
                },
                format="json",
            )

        assert response.status_code == status.HTTP_200_OK
        integration.refresh_from_db()
        credentials = decrypt_credentials(integration.credentials_encrypted)
        assert credentials["access_token"] == "xoxb-new"
        assert credentials["refresh_token"] == "refresh-new"
        assert integration.token_expires_at is not None

    def test_slack_channels_auth_required(self, anonymous_client, admin_a, org_a):
        integration = Integration.objects.create(
            organization=org_a,
            created_by=admin_a,
            name="Slack OAuth",
            connector_type=Integration.ConnectorType.SLACK,
            config={"channel_id": "COPS"},
            credentials_encrypted=encrypt_credentials({"access_token": "xoxb-new"}),
        )

        response = anonymous_client.get(
            f"/api/v1/integrations/{integration.id}/slack/channels/"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_viewer_blocked_from_slack_channels(self, viewer_a_client, admin_a, org_a):
        integration = Integration.objects.create(
            organization=org_a,
            created_by=admin_a,
            name="Slack OAuth",
            connector_type=Integration.ConnectorType.SLACK,
            config={"channel_id": "COPS"},
            credentials_encrypted=encrypt_credentials({"access_token": "xoxb-new"}),
        )

        response = viewer_a_client.get(
            f"/api/v1/integrations/{integration.id}/slack/channels/"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cross_org_slack_channels_returns_404(
        self, admin_a_client, operator_b, org_b
    ):
        integration = Integration.objects.create(
            organization=org_b,
            created_by=operator_b,
            name="Other Org Slack",
            connector_type=Integration.ConnectorType.SLACK,
            config={"channel_id": "COPS"},
            credentials_encrypted=encrypt_credentials({"access_token": "xoxb-new"}),
        )

        response = admin_a_client.get(
            f"/api/v1/integrations/{integration.id}/slack/channels/"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_slack_channels_non_slack_integration_returns_400(
        self, admin_a_client, admin_a, org_a
    ):
        integration = Integration.objects.create(
            organization=org_a,
            created_by=admin_a,
            name="Teams Connector",
            connector_type=Integration.ConnectorType.TEAMS,
            config={"message_template": "x"},
            credentials_encrypted=encrypt_credentials({"webhook_url": "https://x"}),
        )

        response = admin_a_client.get(
            f"/api/v1/integrations/{integration.id}/slack/channels/"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_slack_channels_success_returns_public_channel_list(
        self, admin_a_client, admin_a, org_a
    ):
        integration = Integration.objects.create(
            organization=org_a,
            created_by=admin_a,
            name="Slack OAuth",
            connector_type=Integration.ConnectorType.SLACK,
            config={"channel_id": "COPS"},
            credentials_encrypted=encrypt_credentials({"access_token": "xoxb-new"}),
        )

        with patch(
            "api.services.integration_connectors.httpx.Client.get",
            return_value=httpx.Response(
                status_code=200,
                json={
                    "ok": True,
                    "channels": [
                        {
                            "id": "COPS",
                            "name": "ops-alerts",
                            "is_channel": True,
                            "is_private": False,
                        },
                        {
                            "id": "GPRIV",
                            "name": "private-room",
                            "is_channel": True,
                            "is_private": True,
                        },
                    ],
                },
            ),
        ):
            response = admin_a_client.get(
                f"/api/v1/integrations/{integration.id}/slack/channels/"
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["channels"] == [{"id": "COPS", "name": "ops-alerts"}]

    def test_slack_channels_upstream_failure_returns_502(
        self, admin_a_client, admin_a, org_a
    ):
        integration = Integration.objects.create(
            organization=org_a,
            created_by=admin_a,
            name="Slack OAuth",
            connector_type=Integration.ConnectorType.SLACK,
            config={"channel_id": "COPS"},
            credentials_encrypted=encrypt_credentials({"access_token": "xoxb-new"}),
        )

        with patch(
            "api.services.integration_connectors.httpx.Client.get",
            side_effect=httpx.HTTPError("slack down"),
        ):
            response = admin_a_client.get(
                f"/api/v1/integrations/{integration.id}/slack/channels/"
            )

        assert response.status_code == status.HTTP_502_BAD_GATEWAY

    def test_slack_channels_without_token_returns_400(
        self, admin_a_client, admin_a, org_a
    ):
        integration = Integration.objects.create(
            organization=org_a,
            created_by=admin_a,
            name="Slack OAuth",
            connector_type=Integration.ConnectorType.SLACK,
            config={"channel_id": "COPS"},
            credentials_encrypted=encrypt_credentials({}),
        )

        response = admin_a_client.get(
            f"/api/v1/integrations/{integration.id}/slack/channels/"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_slack_test_auth_required(self, anonymous_client, admin_a, org_a):
        integration = Integration.objects.create(
            organization=org_a,
            created_by=admin_a,
            name="Slack OAuth",
            connector_type=Integration.ConnectorType.SLACK,
            config={"channel_id": "COPS"},
            credentials_encrypted=encrypt_credentials({"access_token": "xoxb-new"}),
        )

        response = anonymous_client.post(
            f"/api/v1/integrations/{integration.id}/slack/test/",
            {"channel_id": "COPS"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_viewer_blocked_from_slack_test(self, viewer_a_client, admin_a, org_a):
        integration = Integration.objects.create(
            organization=org_a,
            created_by=admin_a,
            name="Slack OAuth",
            connector_type=Integration.ConnectorType.SLACK,
            config={"channel_id": "COPS"},
            credentials_encrypted=encrypt_credentials({"access_token": "xoxb-new"}),
        )

        response = viewer_a_client.post(
            f"/api/v1/integrations/{integration.id}/slack/test/",
            {"channel_id": "COPS"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cross_org_slack_test_returns_404(self, admin_a_client, operator_b, org_b):
        integration = Integration.objects.create(
            organization=org_b,
            created_by=operator_b,
            name="Other Org Slack",
            connector_type=Integration.ConnectorType.SLACK,
            config={"channel_id": "COPS"},
            credentials_encrypted=encrypt_credentials({"access_token": "xoxb-new"}),
        )

        response = admin_a_client.post(
            f"/api/v1/integrations/{integration.id}/slack/test/",
            {"channel_id": "COPS"},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_slack_test_success_logs_attempt(self, admin_a_client, admin_a, org_a):
        integration = Integration.objects.create(
            organization=org_a,
            created_by=admin_a,
            name="Slack OAuth",
            connector_type=Integration.ConnectorType.SLACK,
            config={"channel_id": "COPS"},
            credentials_encrypted=encrypt_credentials({"access_token": "xoxb-new"}),
        )

        with patch(
            "api.services.integration_connectors.httpx.Client.post",
            return_value=httpx.Response(status_code=200, json={"ok": True}),
        ):
            response = admin_a_client.post(
                f"/api/v1/integrations/{integration.id}/slack/test/",
                {"channel_id": "COPS"},
                format="json",
            )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["accepted"] is True
        assert payload["delivery_id"]

        delivery = IntegrationDelivery.objects.get(id=payload["delivery_id"])
        assert delivery.status == IntegrationDelivery.Status.DELIVERED
        assert delivery.attempt_count == 1
        attempt = IntegrationDeliveryAttempt.objects.get(delivery=delivery)
        assert attempt.status == IntegrationDeliveryAttempt.Status.SUCCESS

    def test_slack_test_failure_logs_failed_attempt(
        self, admin_a_client, admin_a, org_a
    ):
        integration = Integration.objects.create(
            organization=org_a,
            created_by=admin_a,
            name="Slack OAuth",
            connector_type=Integration.ConnectorType.SLACK,
            config={"channel_id": "COPS"},
            credentials_encrypted=encrypt_credentials({"access_token": "xoxb-new"}),
        )

        with patch(
            "api.services.integration_connectors.httpx.Client.post",
            return_value=httpx.Response(
                status_code=200,
                json={"ok": False, "error": "channel_not_found"},
            ),
        ):
            response = admin_a_client.post(
                f"/api/v1/integrations/{integration.id}/slack/test/",
                {"channel_id": "CMISSING"},
                format="json",
            )

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        delivery = IntegrationDelivery.objects.latest("created_at")
        assert delivery.status == IntegrationDelivery.Status.FAILED
        attempt = IntegrationDeliveryAttempt.objects.get(delivery=delivery)
        assert attempt.status == IntegrationDeliveryAttempt.Status.FAILED

    def test_slack_test_missing_channel_returns_400(
        self, admin_a_client, admin_a, org_a
    ):
        integration = Integration.objects.create(
            organization=org_a,
            created_by=admin_a,
            name="Slack OAuth",
            connector_type=Integration.ConnectorType.SLACK,
            config={},
            credentials_encrypted=encrypt_credentials({"access_token": "xoxb-new"}),
        )

        response = admin_a_client.post(
            f"/api/v1/integrations/{integration.id}/slack/test/",
            {},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
