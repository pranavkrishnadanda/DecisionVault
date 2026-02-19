import pytest
from rest_framework import status
from rest_framework.test import APIClient

from api.models import Organization, OrganizationMembership, OrganizationRole
from decisions.models import Decision, DecisionStatus


@pytest.fixture
def org_a(db):
    return Organization.objects.create(name="Org A")


@pytest.fixture
def org_b(db):
    return Organization.objects.create(name="Org B")


@pytest.fixture
def user_a(django_user_model, org_a):
    user = django_user_model.objects.create_user(
        username="org-a-user",
        email="org-a@example.com",
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
def user_b(django_user_model, org_b):
    user = django_user_model.objects.create_user(
        username="org-b-user",
        email="org-b@example.com",
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
def client_a(user_a):
    client = APIClient()
    client.force_authenticate(user=user_a)
    return client


@pytest.fixture
def client_b(user_b):
    client = APIClient()
    client.force_authenticate(user=user_b)
    return client


@pytest.mark.django_db
class TestOrganizationIsolation:
    def test_decision_list_is_organization_scoped(self, client_a, client_b, org_a, org_b, user_a, user_b):
        Decision.objects.create(
            organization=org_a,
            title="A Decision",
            description="Org A only",
            status=DecisionStatus.DRAFT,
            created_by=str(user_a.id),
        )
        Decision.objects.create(
            organization=org_b,
            title="B Decision",
            description="Org B only",
            status=DecisionStatus.DRAFT,
            created_by=str(user_b.id),
        )

        response_a = client_a.get("/api/v1/decisions/")
        response_b = client_b.get("/api/v1/decisions/")

        assert response_a.status_code == status.HTTP_200_OK
        assert response_b.status_code == status.HTTP_200_OK
        assert [item["title"] for item in response_a.json()] == ["A Decision"]
        assert [item["title"] for item in response_b.json()] == ["B Decision"]

    def test_cross_org_retrieve_returns_404(self, client_b, org_a, user_a):
        decision = Decision.objects.create(
            organization=org_a,
            title="A Secret",
            description="Org A only",
            status=DecisionStatus.DRAFT,
            created_by=str(user_a.id),
        )

        response = client_b.get(f"/api/v1/decisions/{decision.id}/")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cross_org_submit_returns_404(self, client_b, org_a, user_a):
        decision = Decision.objects.create(
            organization=org_a,
            title="A Submit",
            description="Org A only",
            status=DecisionStatus.DRAFT,
            created_by=str(user_a.id),
        )

        response = client_b.post(f"/api/v1/decisions/{decision.id}/submit/", {}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
