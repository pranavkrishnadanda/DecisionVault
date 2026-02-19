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


@pytest.fixture
def org_a(db):
    return Organization.objects.create(name="Delivery Org A")


@pytest.fixture
def org_b(db):
    return Organization.objects.create(name="Delivery Org B")


@pytest.fixture
def admin_a(django_user_model, org_a):
    user = django_user_model.objects.create_user(
        username="delivery-admin-a",
        email="delivery-admin-a@example.com",
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
        username="delivery-operator-a",
        email="delivery-operator-a@example.com",
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
        username="delivery-viewer-a",
        email="delivery-viewer-a@example.com",
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
        username="delivery-operator-b",
        email="delivery-operator-b@example.com",
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
def operator_a_client(operator_a):
    client = APIClient()
    client.force_authenticate(user=operator_a)
    return client


@pytest.fixture
def viewer_a_client(viewer_a):
    client = APIClient()
    client.force_authenticate(user=viewer_a)
    return client


@pytest.fixture
def anonymous_client():
    return APIClient()


@pytest.fixture
def base_subscription(org_a, admin_a):
    return WebhookSubscription.objects.create(
        organization=org_a,
        created_by=admin_a,
        target_url="https://a.example.com/hooks",
        signing_secret="super-secret-123456",
        events=["decision.created"],
        is_active=True,
    )


@pytest.mark.django_db
class TestWebhookDeliveriesAPI:
    def test_list_requires_auth(self, anonymous_client):
        response = anonymous_client.get("/api/v1/webhook-deliveries/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_is_paginated_and_org_scoped(
        self, admin_a_client, org_a, org_b, admin_a, operator_b
    ):
        sub_a = WebhookSubscription.objects.create(
            organization=org_a,
            created_by=admin_a,
            target_url="https://a.example.com/hooks",
            signing_secret="super-secret-123456",
            events=["decision.created"],
            is_active=True,
        )
        sub_b = WebhookSubscription.objects.create(
            organization=org_b,
            created_by=operator_b,
            target_url="https://b.example.com/hooks",
            signing_secret="other-secret-123456",
            events=["decision.created"],
            is_active=True,
        )

        WebhookDelivery.objects.create(
            organization=org_a,
            subscription=sub_a,
            event_type="decision.created",
            payload={"decision_id": "a-1"},
        )
        WebhookDelivery.objects.create(
            organization=org_a,
            subscription=sub_a,
            event_type="decision.created",
            payload={"decision_id": "a-2"},
        )
        WebhookDelivery.objects.create(
            organization=org_b,
            subscription=sub_b,
            event_type="decision.created",
            payload={"decision_id": "b-1"},
        )

        response = admin_a_client.get("/api/v1/webhook-deliveries/?page_size=1")

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert set(body.keys()) == {"count", "next", "previous", "results"}
        assert body["count"] == 2
        assert len(body["results"]) == 1

    def test_detail_is_org_scoped_and_hides_secret(
        self, admin_a_client, org_a, org_b, admin_a, operator_b
    ):
        sub_b = WebhookSubscription.objects.create(
            organization=org_b,
            created_by=operator_b,
            target_url="https://b.example.com/hooks",
            signing_secret="other-secret-123456",
            events=["decision.created"],
            is_active=True,
        )
        delivery = WebhookDelivery.objects.create(
            organization=org_b,
            subscription=sub_b,
            event_type="decision.created",
            payload={"decision_id": "b-1"},
        )

        response = admin_a_client.get(f"/api/v1/webhook-deliveries/{delivery.id}/")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_detail_includes_attempt_history_without_secret(
        self, admin_a_client, org_a, admin_a
    ):
        subscription = WebhookSubscription.objects.create(
            organization=org_a,
            created_by=admin_a,
            target_url="https://a.example.com/hooks",
            signing_secret="super-secret-123456",
            events=["decision.created"],
            is_active=True,
        )
        delivery = WebhookDelivery.objects.create(
            organization=org_a,
            subscription=subscription,
            event_type="decision.created",
            payload={"decision_id": "a-1"},
            status=WebhookDelivery.Status.FAILED,
            attempt_count=1,
            max_attempts=1,
            last_error="timeout",
        )
        WebhookDeliveryAttempt.objects.create(
            organization=org_a,
            delivery=delivery,
            attempt_number=1,
            status=WebhookDeliveryAttempt.Status.FAILED,
            error_message="timeout",
        )

        response = admin_a_client.get(f"/api/v1/webhook-deliveries/{delivery.id}/")

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["id"] == str(delivery.id)
        assert body["subscription"]["id"] == str(subscription.id)
        assert "signing_secret" not in body
        assert len(body["attempts"]) == 1

    def test_viewer_cannot_replay(self, viewer_a_client, base_subscription, org_a):
        delivery = WebhookDelivery.objects.create(
            organization=org_a,
            subscription=base_subscription,
            event_type="decision.created",
            payload={"decision_id": "a-1"},
            status=WebhookDelivery.Status.FAILED,
        )

        response = viewer_a_client.post(
            f"/api/v1/webhook-deliveries/{delivery.id}/replay/", {}, format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_replay_fails_for_delivered(
        self, operator_a_client, base_subscription, org_a
    ):
        delivery = WebhookDelivery.objects.create(
            organization=org_a,
            subscription=base_subscription,
            event_type="decision.created",
            payload={"decision_id": "a-1"},
            status=WebhookDelivery.Status.DELIVERED,
            attempt_count=1,
            max_attempts=1,
        )

        response = operator_a_client.post(
            f"/api/v1/webhook-deliveries/{delivery.id}/replay/", {}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "status" in response.json()

    def test_replay_resets_failed_delivery_and_requeues(
        self, operator_a_client, base_subscription, org_a
    ):
        delivery = WebhookDelivery.objects.create(
            organization=org_a,
            subscription=base_subscription,
            event_type="decision.created",
            payload={"decision_id": "a-1"},
            status=WebhookDelivery.Status.FAILED,
            attempt_count=2,
            max_attempts=2,
            last_error="http_500",
        )
        WebhookDeliveryAttempt.objects.create(
            organization=org_a,
            delivery=delivery,
            attempt_number=1,
            status=WebhookDeliveryAttempt.Status.FAILED,
            error_message="http_500",
        )
        WebhookDeliveryAttempt.objects.create(
            organization=org_a,
            delivery=delivery,
            attempt_number=2,
            status=WebhookDeliveryAttempt.Status.FAILED,
            error_message="http_500",
        )

        with pytest.MonkeyPatch.context() as mp:
            calls = []

            def fake_enqueue(delivery_id: str):
                calls.append(delivery_id)
                return True

            mp.setattr(
                "api.services.webhook_dispatcher.enqueue_webhook_delivery",
                fake_enqueue,
            )
            response = operator_a_client.post(
                f"/api/v1/webhook-deliveries/{delivery.id}/replay/",
                {},
                format="json",
            )

        assert response.status_code == status.HTTP_202_ACCEPTED
        delivery.refresh_from_db()
        assert delivery.status == WebhookDelivery.Status.PENDING
        assert delivery.max_attempts == 3
        assert delivery.attempt_count == 2
        assert calls == [str(delivery.id)]
        assert WebhookDeliveryAttempt.objects.filter(delivery=delivery).count() == 2

    def test_replay_cross_org_returns_404(self, admin_a_client, org_b, operator_b):
        subscription = WebhookSubscription.objects.create(
            organization=org_b,
            created_by=operator_b,
            target_url="https://b.example.com/hooks",
            signing_secret="other-secret-123456",
            events=["decision.created"],
            is_active=True,
        )
        delivery = WebhookDelivery.objects.create(
            organization=org_b,
            subscription=subscription,
            event_type="decision.created",
            payload={"decision_id": "b-1"},
            status=WebhookDelivery.Status.FAILED,
        )

        response = admin_a_client.post(
            f"/api/v1/webhook-deliveries/{delivery.id}/replay/", {}, format="json"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
