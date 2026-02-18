"""JWT authentication and authorization tests for Phase 2.5."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from decisions.models import Decision, DecisionStatus


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(
        username="jwt-user",
        email="jwt-user@example.com",
        password="pass1234",
    )


@pytest.fixture
def other_user(django_user_model):
    return django_user_model.objects.create_user(
        username="jwt-other",
        email="jwt-other@example.com",
        password="pass1234",
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestJWTTokenEndpoints:
    def test_obtain_token_returns_access_and_refresh(self, api_client, user):
        response = api_client.post(
            "/api/v1/auth/token/",
            {"username": user.username, "password": "pass1234"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access" in data
        assert "refresh" in data

    def test_obtain_token_invalid_credentials_returns_401(self, api_client, user):
        response = api_client.post(
            "/api/v1/auth/token/",
            {"username": user.username, "password": "wrong-password"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token_returns_new_access(self, api_client, user):
        token_response = api_client.post(
            "/api/v1/auth/token/",
            {"username": user.username, "password": "pass1234"},
            format="json",
        )
        refresh_token = token_response.json()["refresh"]

        response = api_client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": refresh_token},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.json()


@pytest.mark.django_db
class TestDecisionAuthorizationWithJWT:
    @staticmethod
    def _auth_client(username: str, password: str) -> APIClient:
        client = APIClient()
        token_response = client.post(
            "/api/v1/auth/token/",
            {"username": username, "password": password},
            format="json",
        )
        assert token_response.status_code == status.HTTP_200_OK
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token_response.json()['access']}"
        )
        return client

    def test_create_decision_with_jwt_sets_created_by_user_id(self, user):
        client = self._auth_client(user.username, "pass1234")

        response = client.post(
            "/api/v1/decisions/",
            {
                "title": "JWT decision",
                "description": "Auth test",
                "metadata": {"case": "jwt"},
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

        decision = Decision.objects.get(id=response.json()["id"])
        assert decision.created_by == str(user.id)

    def test_submit_decision_without_jwt_returns_401(self, user):
        decision = Decision.objects.create(
            title="Needs auth",
            description="Submit should require token",
            created_by=str(user.id),
            status=DecisionStatus.DRAFT,
        )
        client = APIClient()

        response = client.post(
            f"/api/v1/decisions/{decision.id}/submit/", {}, format="json"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_submit_decision_as_non_owner_forbidden(self, user, other_user):
        decision = Decision.objects.create(
            title="Owner guarded",
            description="Submit should be owner-only",
            created_by=str(user.id),
            status=DecisionStatus.DRAFT,
        )
        other_client = self._auth_client(other_user.username, "pass1234")

        response = other_client.post(
            f"/api/v1/decisions/{decision.id}/submit/", {}, format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
