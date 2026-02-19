from datetime import timedelta

import pytest
from django.db import connection
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from api.models import (
    Organization,
    OrganizationMembership,
    OrganizationRole,
    RefreshToken,
)


@pytest.fixture(autouse=True)
def ensure_refresh_token_table_exists(db):
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('refresh_tokens')")
        exists = cursor.fetchone()[0] is not None

    if exists:
        return

    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(RefreshToken)


@pytest.fixture
def org_a(db):
    return Organization.objects.create(name="Auth Persistence Org A")


@pytest.fixture
def org_b(db):
    return Organization.objects.create(name="Auth Persistence Org B")


@pytest.fixture
def user_a(django_user_model, org_a):
    user = django_user_model.objects.create_user(
        username="persist-user-a",
        email="persist-a@example.com",
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
def user_b(django_user_model, org_b):
    user = django_user_model.objects.create_user(
        username="persist-user-b",
        email="persist-b@example.com",
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
class TestRefreshFlow:
    def test_login_sets_refresh_cookie_and_returns_access(self, user_a):
        client = APIClient()

        response = client.post(
            "/api/v1/auth/token/",
            {"username": user_a.username, "password": "pass1234"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.json()
        assert "refresh" not in response.json()
        assert "dv_refresh" in response.cookies

        cookie = response.cookies["dv_refresh"]
        assert cookie["httponly"]
        assert cookie["samesite"] == "Lax"

    def test_refresh_with_valid_cookie_rotates_and_returns_new_access(self, user_a):
        client = APIClient()
        login = client.post(
            "/api/v1/auth/token/",
            {"username": user_a.username, "password": "pass1234"},
            format="json",
        )
        original_cookie = login.cookies["dv_refresh"].value

        response = client.post("/api/v1/auth/refresh/", {}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.json()
        assert "refresh" not in response.json()
        assert "dv_refresh" in response.cookies
        assert response.cookies["dv_refresh"].value != original_cookie

        assert RefreshToken.objects.filter(revoked=False).count() == 1
        assert RefreshToken.objects.filter(revoked=True).count() == 1

    def test_refresh_fails_with_revoked_cookie(self, user_a):
        client = APIClient()
        client.post(
            "/api/v1/auth/token/",
            {"username": user_a.username, "password": "pass1234"},
            format="json",
        )

        token_row = RefreshToken.objects.order_by("-created_at").first()
        assert token_row is not None
        token_row.revoked = True
        token_row.save(update_fields=["revoked", "updated_at"])

        response = client.post("/api/v1/auth/refresh/", {}, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_fails_with_expired_cookie(self, user_a):
        client = APIClient()
        client.post(
            "/api/v1/auth/token/",
            {"username": user_a.username, "password": "pass1234"},
            format="json",
        )

        token_row = RefreshToken.objects.order_by("-created_at").first()
        assert token_row is not None
        token_row.expires_at = timezone.now() - timedelta(minutes=1)
        token_row.save(update_fields=["expires_at", "updated_at"])

        response = client.post("/api/v1/auth/refresh/", {}, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_revokes_cookie_token_and_clears_cookie(self, user_a):
        client = APIClient()
        client.post(
            "/api/v1/auth/token/",
            {"username": user_a.username, "password": "pass1234"},
            format="json",
        )

        response = client.post("/api/v1/auth/logout/", {}, format="json")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert RefreshToken.objects.filter(revoked=False).count() == 0
        assert "dv_refresh" in response.cookies
        assert response.cookies["dv_refresh"].value == ""

    def test_refresh_with_cross_org_membership_change_is_blocked(self, user_a, org_b):
        client = APIClient()
        client.post(
            "/api/v1/auth/token/",
            {"username": user_a.username, "password": "pass1234"},
            format="json",
        )

        membership = OrganizationMembership.objects.get(user=user_a)
        membership.organization = org_b
        membership.role = OrganizationRole.VIEWER
        membership.save(update_fields=["organization", "role", "updated_at"])

        response = client.post("/api/v1/auth/refresh/", {}, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
