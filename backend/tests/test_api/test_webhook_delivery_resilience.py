from datetime import timedelta
from unittest.mock import patch

import httpx
import pytest
from django.utils import timezone

from api.models import (
    Organization,
    OrganizationMembership,
    OrganizationRole,
    WebhookDelivery,
    WebhookDeliveryAttempt,
    WebhookSubscription,
)
from api.services.webhook_worker import (
    BASE_RETRY_DELAY_SECONDS,
    CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    RATE_LIMIT_WINDOW_SECONDS,
    SUBSCRIPTION_RATE_LIMIT_PER_WINDOW,
    process_webhook_delivery,
)


@pytest.fixture
def org_a(db):
    return Organization.objects.create(name="Resilience Org A")


@pytest.fixture
def admin_a(django_user_model, org_a):
    user = django_user_model.objects.create_user(
        username="resilience-admin-a",
        email="resilience-admin-a@example.com",
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
def subscription(org_a, admin_a):
    return WebhookSubscription.objects.create(
        organization=org_a,
        created_by=admin_a,
        target_url="https://a.example.com/hooks",
        signing_secret="resilience-secret-123456",
        events=["decision.created"],
        is_active=True,
    )


@pytest.mark.django_db
class TestWebhookResilience:
    def test_worker_respects_next_retry_at_and_skips_early_send(self, org_a, subscription):
        future = timezone.now() + timedelta(minutes=5)
        delivery = WebhookDelivery.objects.create(
            organization=org_a,
            subscription=subscription,
            event_type="decision.created",
            payload={"decision_id": "d-1"},
            status=WebhookDelivery.Status.PENDING,
            next_retry_at=future,
        )

        with patch("api.services.webhook_worker.httpx.Client.post") as mock_post:
            processed = process_webhook_delivery(str(delivery.id))

        delivery.refresh_from_db()
        assert processed is False
        assert mock_post.call_count == 0
        assert delivery.attempt_count == 0
        assert delivery.next_retry_at == future

    def test_timeout_uses_exponential_backoff_schedule(self, org_a, subscription):
        delivery = WebhookDelivery.objects.create(
            organization=org_a,
            subscription=subscription,
            event_type="decision.created",
            payload={"decision_id": "d-2"},
            status=WebhookDelivery.Status.PENDING,
            max_attempts=4,
        )

        with patch(
            "api.services.webhook_worker.httpx.Client.post",
            side_effect=httpx.TimeoutException("timeout"),
        ):
            process_webhook_delivery(str(delivery.id))

        delivery.refresh_from_db()
        first_delay = delivery.next_retry_at - delivery.last_attempt_at
        assert int(first_delay.total_seconds()) == BASE_RETRY_DELAY_SECONDS

        delivery.next_retry_at = timezone.now() - timedelta(seconds=1)
        delivery.save(update_fields=["next_retry_at"])

        with patch(
            "api.services.webhook_worker.httpx.Client.post",
            side_effect=httpx.TimeoutException("timeout"),
        ):
            process_webhook_delivery(str(delivery.id))

        delivery.refresh_from_db()
        second_delay = delivery.next_retry_at - delivery.last_attempt_at
        assert int(second_delay.total_seconds()) == BASE_RETRY_DELAY_SECONDS * 2

    def test_circuit_breaker_disables_subscription_after_failure_window_threshold(
        self, org_a, subscription
    ):
        for idx in range(CIRCUIT_BREAKER_FAILURE_THRESHOLD - 1):
            prior_delivery = WebhookDelivery.objects.create(
                organization=org_a,
                subscription=subscription,
                event_type="decision.created",
                payload={"decision_id": f"prior-{idx}"},
                status=WebhookDelivery.Status.FAILED,
            )
            WebhookDeliveryAttempt.objects.create(
                organization=org_a,
                delivery=prior_delivery,
                attempt_number=1,
                status=WebhookDeliveryAttempt.Status.FAILED,
                error_message="http_500",
            )

        delivery = WebhookDelivery.objects.create(
            organization=org_a,
            subscription=subscription,
            event_type="decision.created",
            payload={"decision_id": "breaker-target"},
            status=WebhookDelivery.Status.PENDING,
            max_attempts=3,
        )

        response = httpx.Response(status_code=503)
        with patch("api.services.webhook_worker.httpx.Client.post", return_value=response):
            process_webhook_delivery(str(delivery.id))

        subscription.refresh_from_db()
        assert subscription.is_active is False

    def test_terminal_failure_routes_to_dead_letter_queue(self, org_a, subscription):
        delivery = WebhookDelivery.objects.create(
            organization=org_a,
            subscription=subscription,
            event_type="decision.created",
            payload={"decision_id": "d-4"},
            status=WebhookDelivery.Status.PENDING,
            attempt_count=2,
            max_attempts=3,
        )

        with patch(
            "api.services.webhook_worker.httpx.Client.post",
            side_effect=httpx.TimeoutException("timeout"),
        ), patch("api.services.webhook_worker.enqueue_webhook_dead_letter") as mock_dlq:
            process_webhook_delivery(str(delivery.id))

        delivery.refresh_from_db()
        assert delivery.status == WebhookDelivery.Status.FAILED
        mock_dlq.assert_called_once_with(str(delivery.id), reason="timeout")

    def test_subscription_rate_limit_throttles_delivery(self, org_a, subscription):
        window_floor = timezone.now() - timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS - 5)

        for idx in range(SUBSCRIPTION_RATE_LIMIT_PER_WINDOW):
            prior_delivery = WebhookDelivery.objects.create(
                organization=org_a,
                subscription=subscription,
                event_type="decision.created",
                payload={"decision_id": f"throttle-{idx}"},
                status=WebhookDelivery.Status.DELIVERED,
            )
            attempt = WebhookDeliveryAttempt.objects.create(
                organization=org_a,
                delivery=prior_delivery,
                attempt_number=1,
                status=WebhookDeliveryAttempt.Status.SUCCESS,
            )
            WebhookDeliveryAttempt.objects.filter(id=attempt.id).update(created_at=window_floor)

        target = WebhookDelivery.objects.create(
            organization=org_a,
            subscription=subscription,
            event_type="decision.created",
            payload={"decision_id": "throttle-target"},
            status=WebhookDelivery.Status.PENDING,
        )

        with patch("api.services.webhook_worker.httpx.Client.post") as mock_post:
            processed = process_webhook_delivery(str(target.id))

        target.refresh_from_db()
        assert processed is False
        assert mock_post.call_count == 0
        assert target.attempt_count == 0
        assert target.status == WebhookDelivery.Status.PENDING
        assert target.next_retry_at is not None
