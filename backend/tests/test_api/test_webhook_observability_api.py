import pytest
from rest_framework import status
from rest_framework.test import APIClient

from api.models import (
    Organization,
    OrganizationMembership,
    OrganizationRole,
    WebhookDelivery,
    WebhookDeliveryAttempt,
    WebhookSubscription,
)
from decisions.models import AuditLog


@pytest.fixture
def org_a(db):
    return Organization.objects.create(name="Observability Org A")


@pytest.fixture
def org_b(db):
    return Organization.objects.create(name="Observability Org B")


@pytest.fixture
def admin_a(django_user_model, org_a):
    user = django_user_model.objects.create_user(
        username="obs-admin-a",
        email="obs-admin-a@example.com",
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
def operator_a(django_user_model, org_a):
    user = django_user_model.objects.create_user(
        username="obs-operator-a",
        email="obs-operator-a@example.com",
        password="pass1234",
    )
    OrganizationMembership.objects.filter(user=user).delete()
    OrganizationMembership.objects.create(
        user=user,
        organization=org_a,
        role=OrganizationRole.OPERATOR,
    )
    return user


@pytest.fixture
def viewer_a(django_user_model, org_a):
    user = django_user_model.objects.create_user(
        username="obs-viewer-a",
        email="obs-viewer-a@example.com",
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
        username="obs-operator-b",
        email="obs-operator-b@example.com",
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
def admin_client(admin_a):
    client = APIClient()
    client.force_authenticate(user=admin_a)
    return client


@pytest.fixture
def operator_client(operator_a):
    client = APIClient()
    client.force_authenticate(user=operator_a)
    return client


@pytest.fixture
def viewer_client(viewer_a):
    client = APIClient()
    client.force_authenticate(user=viewer_a)
    return client


@pytest.fixture
def base_subscription(org_a, admin_a):
    return WebhookSubscription.objects.create(
        organization=org_a,
        created_by=admin_a,
        target_url="https://obs.example.com/hooks",
        signing_secret="obs-secret-123456",
        events=["decision.created"],
        is_active=True,
    )


@pytest.mark.django_db
class TestWebhookObservabilityAPI:
    def test_metrics_correctness(self, admin_client, org_a, admin_a):
        healthy_subscription = WebhookSubscription.objects.create(
            organization=org_a,
            created_by=admin_a,
            target_url="https://healthy.example.com/hooks",
            signing_secret="healthy-secret-123456",
            events=["decision.created"],
            is_active=True,
        )
        broken_subscription = WebhookSubscription.objects.create(
            organization=org_a,
            created_by=admin_a,
            target_url="https://broken.example.com/hooks",
            signing_secret="broken-secret-123456",
            events=["decision.created"],
            is_active=False,
        )

        WebhookDelivery.objects.create(
            organization=org_a,
            subscription=healthy_subscription,
            event_type="decision.created",
            payload={"decision_id": "d-1"},
            status=WebhookDelivery.Status.DELIVERED,
            attempt_count=1,
            max_attempts=3,
        )
        WebhookDelivery.objects.create(
            organization=org_a,
            subscription=broken_subscription,
            event_type="decision.created",
            payload={"decision_id": "d-2"},
            status=WebhookDelivery.Status.FAILED,
            attempt_count=3,
            max_attempts=3,
        )

        response = admin_client.get("/api/v1/webhook-deliveries/metrics/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["delivery_success_rate"] == 50.0
        assert data["retry_count"] == 2
        assert data["dlq_count"] == 1
        assert data["breaker_status"] == {"open": 1, "closed": 1}

    def test_timeline_accuracy_contains_attempts_delays_and_throttle_events(
        self, admin_client, org_a, base_subscription
    ):
        delivery = WebhookDelivery.objects.create(
            organization=org_a,
            subscription=base_subscription,
            event_type="decision.created",
            payload={"decision_id": "d-3"},
            status=WebhookDelivery.Status.FAILED,
            attempt_count=2,
            max_attempts=3,
        )
        first_attempt = WebhookDeliveryAttempt.objects.create(
            organization=org_a,
            delivery=delivery,
            attempt_number=1,
            status=WebhookDeliveryAttempt.Status.FAILED,
            error_message="timeout",
        )
        second_attempt = WebhookDeliveryAttempt.objects.create(
            organization=org_a,
            delivery=delivery,
            attempt_number=2,
            status=WebhookDeliveryAttempt.Status.FAILED,
            error_message="http_500",
        )
        AuditLog.objects.create(
            organization=org_a,
            entity_type="webhook_delivery",
            entity_id=delivery.id,
            action="update",
            actor_type="system",
            actor_id="",
            previous_state=None,
            current_state={"status": "pending"},
            metadata={"event": "throttled", "reason": "rate_limit"},
        )

        response = admin_client.get(f"/api/v1/webhook-deliveries/{delivery.id}/timeline/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["delivery_id"] == str(delivery.id)
        assert len(data["events"]) >= 3
        attempt_events = [item for item in data["events"] if item["type"] == "attempt"]
        assert [item["attempt_number"] for item in attempt_events] == [1, 2]
        assert any(item["type"] == "throttle" for item in data["events"])
        assert first_attempt.id is not None
        assert second_attempt.id is not None

    def test_force_retry_permission_and_audit(self, operator_client, viewer_client, org_a, base_subscription):
        delivery = WebhookDelivery.objects.create(
            organization=org_a,
            subscription=base_subscription,
            event_type="decision.created",
            payload={"decision_id": "d-4"},
            status=WebhookDelivery.Status.FAILED,
            attempt_count=3,
            max_attempts=3,
        )

        viewer_response = viewer_client.post(
            f"/api/v1/webhook-deliveries/{delivery.id}/force-retry/", {}, format="json"
        )
        assert viewer_response.status_code == status.HTTP_403_FORBIDDEN

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "api.services.webhook_dispatcher.enqueue_webhook_delivery",
                lambda delivery_id: True,
            )
            operator_response = operator_client.post(
                f"/api/v1/webhook-deliveries/{delivery.id}/force-retry/", {}, format="json"
            )

        assert operator_response.status_code == status.HTTP_202_ACCEPTED
        delivery.refresh_from_db()
        assert delivery.status == WebhookDelivery.Status.PENDING
        assert delivery.max_attempts == 4

        audit = AuditLog.objects.filter(
            entity_type="webhook_delivery",
            entity_id=delivery.id,
            metadata__event="force_retry",
        ).first()
        assert audit is not None

    def test_reactivate_subscription_permission_org_isolation_and_audit(
        self, operator_client, viewer_client, org_a, org_b, admin_a, operator_b
    ):
        subscription_a = WebhookSubscription.objects.create(
            organization=org_a,
            created_by=admin_a,
            target_url="https://inactive-a.example.com/hooks",
            signing_secret="inactive-a-secret-123456",
            events=["decision.created"],
            is_active=False,
        )
        subscription_b = WebhookSubscription.objects.create(
            organization=org_b,
            created_by=operator_b,
            target_url="https://inactive-b.example.com/hooks",
            signing_secret="inactive-b-secret-123456",
            events=["decision.created"],
            is_active=False,
        )

        viewer_response = viewer_client.post(
            f"/api/v1/webhook-subscriptions/{subscription_a.id}/reactivate/",
            {},
            format="json",
        )
        assert viewer_response.status_code == status.HTTP_403_FORBIDDEN

        operator_response = operator_client.post(
            f"/api/v1/webhook-subscriptions/{subscription_a.id}/reactivate/",
            {},
            format="json",
        )
        assert operator_response.status_code == status.HTTP_200_OK
        subscription_a.refresh_from_db()
        assert subscription_a.is_active is True

        cross_org_response = operator_client.post(
            f"/api/v1/webhook-subscriptions/{subscription_b.id}/reactivate/",
            {},
            format="json",
        )
        assert cross_org_response.status_code == status.HTTP_404_NOT_FOUND

        audit = AuditLog.objects.filter(
            entity_type="webhook_subscription",
            entity_id=subscription_a.id,
            metadata__event="reactivated",
        ).first()
        assert audit is not None
