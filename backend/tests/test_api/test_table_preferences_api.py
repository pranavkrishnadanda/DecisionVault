import pytest
from django.db import connection
from rest_framework import status
from rest_framework.test import APIClient

from decisions.models import TablePreference


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(
        username="prefs-user",
        email="prefs-user@example.com",
        password="pass1234",
    )


@pytest.fixture
def other_user(django_user_model):
    return django_user_model.objects.create_user(
        username="prefs-other",
        email="prefs-other@example.com",
        password="pass1234",
    )


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
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
def ensure_table_preference_table_exists(db):
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('table_preferences')")
        exists = cursor.fetchone()[0] is not None

    if exists:
        return

    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(TablePreference)


@pytest.mark.django_db
class TestTablePreferencesAPI:
    def test_auth_required_for_get(self, anonymous_client):
        response = anonymous_client.get("/api/v1/table-preferences/decisions/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_auth_required_for_put(self, anonymous_client):
        response = anonymous_client.put(
            "/api/v1/table-preferences/decisions/",
            {
                "visible_columns": ["id", "status"],
                "column_order": ["id", "status", "workflow", "updated"],
                "density": "compact",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_returns_default_for_new_user(self, api_client):
        response = api_client.get("/api/v1/table-preferences/decisions/")

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["table"] == "decisions"
        assert payload["density"] == "comfortable"
        assert payload["visible_columns"] == ["id", "workflow", "status", "updated"]
        assert payload["column_order"] == ["id", "workflow", "status", "updated"]

    def test_put_creates_and_updates_preferences(self, api_client):
        create_response = api_client.put(
            "/api/v1/table-preferences/decisions/",
            {
                "visible_columns": ["id", "status", "updated"],
                "column_order": ["status", "id", "updated", "workflow"],
                "density": "compact",
            },
            format="json",
        )
        assert create_response.status_code == status.HTTP_200_OK
        create_payload = create_response.json()
        assert create_payload["density"] == "compact"
        assert create_payload["visible_columns"] == ["id", "status", "updated"]

        update_response = api_client.put(
            "/api/v1/table-preferences/decisions/",
            {
                "visible_columns": ["workflow", "status"],
                "column_order": ["workflow", "status", "id", "updated"],
                "density": "spacious",
            },
            format="json",
        )
        assert update_response.status_code == status.HTTP_200_OK
        update_payload = update_response.json()
        assert update_payload["density"] == "spacious"
        assert update_payload["visible_columns"] == ["workflow", "status"]

    def test_preferences_are_isolated_per_user(self, api_client, other_client):
        put_response = api_client.put(
            "/api/v1/table-preferences/decisions/",
            {
                "visible_columns": ["id", "status"],
                "column_order": ["status", "id", "workflow", "updated"],
                "density": "compact",
            },
            format="json",
        )
        assert put_response.status_code == status.HTTP_200_OK

        other_response = other_client.get("/api/v1/table-preferences/decisions/")
        assert other_response.status_code == status.HTTP_200_OK
        other_payload = other_response.json()
        assert other_payload["visible_columns"] == [
            "id",
            "workflow",
            "status",
            "updated",
        ]
        assert other_payload["density"] == "comfortable"

    def test_invalid_payload_rejected(self, api_client):
        invalid_density = api_client.put(
            "/api/v1/table-preferences/decisions/",
            {
                "visible_columns": ["id", "status"],
                "column_order": ["id", "status", "workflow", "updated"],
                "density": "dense",
            },
            format="json",
        )
        assert invalid_density.status_code == status.HTTP_400_BAD_REQUEST

        invalid_visible_columns = api_client.put(
            "/api/v1/table-preferences/decisions/",
            {
                "visible_columns": "id,status",
                "column_order": ["id", "status", "workflow", "updated"],
                "density": "compact",
            },
            format="json",
        )
        assert invalid_visible_columns.status_code == status.HTTP_400_BAD_REQUEST
