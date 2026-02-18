import uuid

import pytest
from django.db import connection
from rest_framework import status
from rest_framework.test import APIClient

from decisions.models import SavedView


@pytest.fixture
def owner_user(django_user_model):
    return django_user_model.objects.create_user(
        username="saved-owner",
        email="saved-owner@example.com",
        password="pass1234",
    )


@pytest.fixture
def other_user(django_user_model):
    return django_user_model.objects.create_user(
        username="saved-other",
        email="saved-other@example.com",
        password="pass1234",
    )


@pytest.fixture
def owner_client(owner_user):
    client = APIClient()
    client.force_authenticate(user=owner_user)
    return client


@pytest.fixture
def other_client(other_user):
    client = APIClient()
    client.force_authenticate(user=other_user)
    return client


@pytest.fixture
def anonymous_client():
    return APIClient()


@pytest.fixture(autouse=True)
def ensure_saved_view_table_exists(db):
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('saved_views')")
        exists = cursor.fetchone()[0] is not None

    if exists:
        return

    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(SavedView)


@pytest.mark.django_db
class TestSavedViewsAPI:
    def test_auth_required_for_listing(self, anonymous_client):
        response = anonymous_client.get("/api/v1/saved-views/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_auth_required_for_create(self, anonymous_client):
        response = anonymous_client.post(
            "/api/v1/saved-views/",
            {"name": "Anonymous", "filters": {"status": "failed"}},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_owner_isolation_for_list(
        self, owner_client, other_client, owner_user, other_user
    ):
        SavedView.objects.create(
            user=owner_user,
            name="Owner View",
            filters={"status": "failed", "q": "fraud"},
        )
        SavedView.objects.create(
            user=other_user,
            name="Other View",
            filters={"status": "pending"},
        )

        owner_response = owner_client.get("/api/v1/saved-views/")
        other_response = other_client.get("/api/v1/saved-views/")

        assert owner_response.status_code == status.HTTP_200_OK
        assert other_response.status_code == status.HTTP_200_OK
        assert [item["name"] for item in owner_response.json()] == ["Owner View"]
        assert [item["name"] for item in other_response.json()] == ["Other View"]

    def test_create_saved_view(self, owner_client):
        payload = {
            "name": "Failed Fraud",
            "filters": {
                "status": "failed",
                "q": "fraud",
                "from": "2026-02-01",
                "to": "2026-02-18",
            },
        }
        response = owner_client.post("/api/v1/saved-views/", payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert body["name"] == "Failed Fraud"
        assert body["filters"] == payload["filters"]
        assert SavedView.objects.filter(id=body["id"]).exists()

    def test_delete_owned_saved_view(self, owner_client, owner_user):
        saved_view = SavedView.objects.create(
            user=owner_user,
            name="Delete Me",
            filters={"status": "failed"},
        )

        response = owner_client.delete(f"/api/v1/saved-views/{saved_view.id}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not SavedView.objects.filter(id=saved_view.id).exists()

    def test_cannot_delete_other_user_saved_view(self, owner_client, other_user):
        saved_view = SavedView.objects.create(
            user=other_user,
            name="Other",
            filters={"status": "pending"},
        )

        response = owner_client.delete(f"/api/v1/saved-views/{saved_view.id}/")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert SavedView.objects.filter(id=saved_view.id).exists()

    def test_invalid_filters_rejected(self, owner_client):
        response = owner_client.post(
            "/api/v1/saved-views/",
            {
                "name": "Broken",
                "filters": {"status": "not-a-valid-status"},
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "filters" in response.json()

    def test_invalid_filter_shape_rejected(self, owner_client):
        response = owner_client.post(
            "/api/v1/saved-views/",
            {
                "name": "Broken",
                "filters": "bad",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "filters" in response.json()

    def test_auth_required_for_delete(self, anonymous_client):
        response = anonymous_client.delete(f"/api/v1/saved-views/{uuid.uuid4()}/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
