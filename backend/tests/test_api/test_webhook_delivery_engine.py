import hmac
import json
from datetime import timedelta
from hashlib import sha256
from unittest.mock import patch

import httpx
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from api.models import (
    Organization,
    OrganizationMembership,
    OrganizationRole,
    WebhookDelivery,
    WebhookDeliveryAttempt,
    WebhookSubscription,
)
from api.services.webhook_dispatcher import dispatch_event_to_webhooks
from api.services.webhook_signing import (
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
    is_timestamp_within_window,
    sign_payload,
)
from api.services.webhook_worker import process_webhook_delivery


@pytest.fixture
def org_a(db):
    return Organization.objects.create(name="Dispatch Org A")


@pytest.fixture
def org_b(db):
    return Organization.objects.create(name="Dispatch Org B")


@pytest.fixture
def admin_a(django_user_model, org_a):
    user = django_user_model.objects.create_user(
        username="dispatch-admin-a",
        email="dispatch-admin-a@example.com",
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
def operator_b(django_user_model, org_b):
    user = django_user_model.objects.create_user(
        username="dispatch-operator-b",
        email="dispatch-operator-b@example.com",
        password="pass1234",
    )
    OrganizationMembership.objects.filter(user=user).delete()
    OrganizationMembership.objects.create(
        user=user,
        organization=org_b,
        role=OrganizationRole.OPERATOR,
    )
    return user


@pytest.mark.django_db
class TestWebhookDispatcher:
    def test_dispatch_creates_deliveries_for_org_scoped_matching_subscriptions(
        self, admin_a, operator_b, org_a, org_b
    ):
        WebhookSubscription.objects.create(
            organization=org_a,
            created_by=admin_a,
            target_url="https://a.example.com/hooks",
            signing_secret="a-secret-123456",
            events=["decision.created"],
            is_active=True,
        )
        WebhookSubscription.objects.create(
            organization=org_a,
            created_by=admin_a,
            target_url="https://a.example.com/disabled",
            signing_secret="a-secret-123456",
            events=["decision.created"],
            is_active=False,
        )
        WebhookSubscription.objects.create(
            organization=org_b,
            created_by=operator_b,
            target_url="https://b.example.com/hooks",
            signing_secret="b-secret-123456",
            events=["decision.created"],
            is_active=True,
        )

        with patch("api.services.webhook_dispatcher.enqueue_webhook_delivery") as mock_enqueue:
            created = dispatch_event_to_webhooks(
                organization=org_a,
                event_type="decision.created",
                payload={"decision_id": "abc"},
            )

        assert created == 1
        deliveries = WebhookDelivery.objects.all()
        assert deliveries.count() == 1
        assert deliveries.first().organization_id == org_a.id
        assert deliveries.first().event_type == "decision.created"
        mock_enqueue.assert_called_once_with(str(deliveries.first().id))


@pytest.mark.django_db
class TestWebhookWorker:
    def test_worker_marks_delivery_delivered_on_2xx(self, admin_a, org_a):
        subscription = WebhookSubscription.objects.create(
            organization=org_a,
            created_by=admin_a,
            target_url="https://example.com/hooks",
            signing_secret="delivery-secret-123456",
            events=["decision.created"],
            is_active=True,
        )
        delivery = WebhookDelivery.objects.create(
            organization=org_a,
            subscription=subscription,
            event_type="decision.created",
            payload={"decision_id": "d-1"},
        )

        response = httpx.Response(status_code=202, headers={"X-Request-ID": "req-1"})

        with patch("api.services.webhook_worker.httpx.Client.post", return_value=response) as mock_post:
            process_webhook_delivery(str(delivery.id))

        delivery.refresh_from_db()
        assert delivery.status == WebhookDelivery.Status.DELIVERED
        assert delivery.attempt_count == 1
        assert delivery.last_response_status == 202

        attempt = WebhookDeliveryAttempt.objects.filter(delivery=delivery).first()
        assert attempt is not None
        assert attempt.status == WebhookDeliveryAttempt.Status.SUCCESS
        assert attempt.response_status == 202

        _, kwargs = mock_post.call_args
        headers = kwargs["headers"]
        assert TIMESTAMP_HEADER in headers
        assert SIGNATURE_HEADER in headers
        assert headers[SIGNATURE_HEADER].startswith("sha256=")

    def test_worker_retries_on_timeout_before_max_attempts(self, admin_a, org_a):
        subscription = WebhookSubscription.objects.create(
            organization=org_a,
            created_by=admin_a,
            target_url="https://example.com/hooks",
            signing_secret="delivery-secret-123456",
            events=["decision.created"],
            is_active=True,
        )
        delivery = WebhookDelivery.objects.create(
            organization=org_a,
            subscription=subscription,
            event_type="decision.created",
            payload={"decision_id": "d-2"},
            max_attempts=3,
        )

        with patch(
            "api.services.webhook_worker.httpx.Client.post",
            side_effect=httpx.TimeoutException("timeout"),
        ):
            process_webhook_delivery(str(delivery.id))

        delivery.refresh_from_db()
        assert delivery.status == WebhookDelivery.Status.PENDING
        assert delivery.attempt_count == 1
        assert delivery.next_retry_at is not None
        assert delivery.last_error == "timeout"

        attempt = WebhookDeliveryAttempt.objects.filter(delivery=delivery).first()
        assert attempt is not None
        assert attempt.status == WebhookDeliveryAttempt.Status.FAILED
        assert attempt.error_message == "timeout"

    def test_worker_fails_delivery_when_max_attempts_reached(self, admin_a, org_a):
        subscription = WebhookSubscription.objects.create(
            organization=org_a,
            created_by=admin_a,
            target_url="https://example.com/hooks",
            signing_secret="delivery-secret-123456",
            events=["decision.created"],
            is_active=True,
        )
        delivery = WebhookDelivery.objects.create(
            organization=org_a,
            subscription=subscription,
            event_type="decision.created",
            payload={"decision_id": "d-3"},
            max_attempts=2,
            attempt_count=1,
        )

        with patch(
            "api.services.webhook_worker.httpx.Client.post",
            side_effect=httpx.TimeoutException("timeout"),
        ):
            process_webhook_delivery(str(delivery.id))

        delivery.refresh_from_db()
        assert delivery.status == WebhookDelivery.Status.FAILED
        assert delivery.attempt_count == 2
        assert delivery.next_retry_at is None


@pytest.mark.django_db
class TestWebhookSigning:
    def test_sign_payload_uses_hmac_sha256(self):
        payload = {"key": "value"}
        timestamp = "1739959200"
        secret = "super-secret-12345"

        signature = sign_payload(payload=payload, secret=secret, timestamp=timestamp)

        serialized = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        expected = hmac.new(
            secret.encode("utf-8"),
            f"{timestamp}.{serialized}".encode("utf-8"),
            sha256,
        ).hexdigest()
        assert signature == f"sha256={expected}"

    def test_timestamp_replay_window_enforced(self):
        now = timezone.now()
        assert is_timestamp_within_window(str(int(now.timestamp())), now=now) is True

        too_old = int((now - timedelta(minutes=6)).timestamp())
        assert is_timestamp_within_window(str(too_old), now=now) is False

        too_far_future = int((now + timedelta(minutes=6)).timestamp())
        assert is_timestamp_within_window(str(too_far_future), now=now) is False


@pytest.mark.django_db
class TestDecisionLifecycleWebhookEmission:
    def test_create_decision_dispatches_webhook_event(self, admin_a):
        client = APIClient()
        client.force_authenticate(user=admin_a)

        with patch("decisions.views.dispatch_event_to_webhooks") as mock_dispatch:
            response = client.post(
                "/api/v1/decisions/",
                {
                    "title": "Webhook test",
                    "description": "create event",
                    "priority": 1,
                },
                format="json",
            )

        assert response.status_code == 201
        mock_dispatch.assert_called_once()
        _, kwargs = mock_dispatch.call_args
        assert kwargs["event_type"] == "decision.created"
