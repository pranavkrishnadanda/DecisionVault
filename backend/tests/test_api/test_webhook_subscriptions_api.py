import uuid

import pytest
from django.db import connection
from rest_framework import status
from rest_framework.test import APIClient

from api.models import (
    Organization,
    OrganizationMembership,
    OrganizationRole,
    WebhookSubscription,
)


@pytest.fixture(autouse=True)
def ensure_webhook_subscription_table_exists(db):
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('webhook_subscriptions')")
        exists = cursor.fetchone()[0] is not None

    if exists:
        return

    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(WebhookSubscription)


@pytest.fixture
def org_a(db):
    return Organization.objects.create(name="Org A")


@pytest.fixture
def org_b(db):
    return Organization.objects.create(name="Org B")


@pytest.fixture
def admin_a(django_user_model, org_a):
    user = django_user_model.objects.create_user(
        username="webhook-admin-a",
        email="webhook-admin-a@example.com",
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
        username="webhook-operator-b",
        email="webhook-operator-b@example.com",
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
def viewer_a(django_user_model, org_a):
    user = django_user_model.objects.create_user(
        username="webhook-viewer-a",
        email="webhook-viewer-a@example.com",
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
def admin_a_client(admin_a):
    client = APIClient()
    client.force_authenticate(user=admin_a)
    return client


@pytest.fixture
def operator_b_client(operator_b):
    client = APIClient()
    client.force_authenticate(user=operator_b)
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
class TestWebhookSubscriptionAPI:
    def test_auth_required_for_list(self, anonymous_client):
        response = anonymous_client.get("/api/v1/webhook-subscriptions/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_auth_required_for_create(self, anonymous_client):
        response = anonymous_client.post(
            "/api/v1/webhook-subscriptions/",
            {
                "target_url": "https://example.com/hooks/decision",
                "signing_secret": "super-secret-key",
                "events": ["decision.created"],
                "is_active": True,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_subscription_scoped_to_membership_org(self, admin_a_client, org_a):
        response = admin_a_client.post(
            "/api/v1/webhook-subscriptions/",
            {
                "target_url": "https://example.com/hooks/decision",
                "signing_secret": "super-secret-key",
                "events": ["decision.created", "decision.completed"],
                "is_active": True,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        payload = response.json()
        assert payload["target_url"] == "https://example.com/hooks/decision"
        assert payload["events"] == ["decision.created", "decision.completed"]
        assert "signing_secret" not in payload

        record = WebhookSubscription.objects.get(id=payload["id"])
        assert record.organization_id == org_a.id

    def test_list_is_organization_scoped(
        self, admin_a_client, operator_b_client, org_a, org_b, admin_a, operator_b
    ):
        WebhookSubscription.objects.create(
            organization=org_a,
            created_by=admin_a,
            target_url="https://a.example.com/webhooks",
            signing_secret="secret-a",
            events=["decision.created"],
            is_active=True,
        )
        WebhookSubscription.objects.create(
            organization=org_b,
            created_by=operator_b,
            target_url="https://b.example.com/webhooks",
            signing_secret="secret-b",
            events=["decision.failed"],
            is_active=True,
        )

        a_response = admin_a_client.get("/api/v1/webhook-subscriptions/")
        b_response = operator_b_client.get("/api/v1/webhook-subscriptions/")

        assert a_response.status_code == status.HTTP_200_OK
        assert b_response.status_code == status.HTTP_200_OK
        assert [item["target_url"] for item in a_response.json()] == [
            "https://a.example.com/webhooks"
        ]
        assert [item["target_url"] for item in b_response.json()] == [
            "https://b.example.com/webhooks"
        ]

    def test_cross_org_retrieve_returns_404(self, admin_a_client, org_b, operator_b):
        subscription = WebhookSubscription.objects.create(
            organization=org_b,
            created_by=operator_b,
            target_url="https://b.example.com/webhooks",
            signing_secret="secret-b",
            events=["decision.failed"],
            is_active=True,
        )

        response = admin_a_client.get(
            f"/api/v1/webhook-subscriptions/{subscription.id}/"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cross_org_delete_returns_404(self, admin_a_client, org_b, operator_b):
        subscription = WebhookSubscription.objects.create(
            organization=org_b,
            created_by=operator_b,
            target_url="https://b.example.com/webhooks",
            signing_secret="secret-b",
            events=["decision.failed"],
            is_active=True,
        )

        response = admin_a_client.delete(
            f"/api/v1/webhook-subscriptions/{subscription.id}/"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert WebhookSubscription.objects.filter(id=subscription.id).exists()

    def test_viewer_cannot_create_subscription(self, viewer_a_client):
        response = viewer_a_client.post(
            "/api/v1/webhook-subscriptions/",
            {
                "target_url": "https://example.com/hooks/decision",
                "signing_secret": "super-secret-key",
                "events": ["decision.created"],
                "is_active": True,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_invalid_event_rejected(self, admin_a_client):
        response = admin_a_client.post(
            "/api/v1/webhook-subscriptions/",
            {
                "target_url": "https://example.com/hooks/decision",
                "signing_secret": "super-secret-key",
                "events": ["not-a-real-event"],
                "is_active": True,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "events" in response.json()

    def test_auth_required_for_delete(self, anonymous_client):
        response = anonymous_client.delete(
            f"/api/v1/webhook-subscriptions/{uuid.uuid4()}/"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
