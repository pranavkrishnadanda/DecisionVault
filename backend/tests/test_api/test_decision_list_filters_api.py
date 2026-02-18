import datetime as dt
import uuid

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from decisions.models import Decision, DecisionStatus


@pytest.fixture
def api_user(django_user_model):
    return django_user_model.objects.create_user(
        username="filters-user",
        email="filters-user@example.com",
        password="pass1234",
    )


@pytest.fixture
def api_client(api_user):
    client = APIClient()
    client.force_authenticate(user=api_user)
    return client


@pytest.fixture
def anonymous_client():
    return APIClient()


@pytest.fixture
def seeded_decisions(api_user):
    user_id = str(api_user.id)
    base = timezone.now()

    created = []
    for index, status_value in enumerate(
        [
            DecisionStatus.DRAFT,
            DecisionStatus.PENDING,
            DecisionStatus.FAILED,
            DecisionStatus.COMPLETED,
            DecisionStatus.FAILED,
        ]
    ):
        decision = Decision.objects.create(
            title=f"Decision {index + 1}",
            description=f"Description {index + 1}",
            status=status_value,
            created_by=user_id,
            metadata={"seq": index + 1},
        )
        Decision.objects.filter(id=decision.id).update(
            updated_at=base - dt.timedelta(hours=index)
        )
        decision.refresh_from_db()
        created.append(decision)

    created[2].title = "Fraud escalation review"
    created[2].description = "Manual fraud escalation path"
    created[2].save(update_fields=["title", "description", "updated_at"])

    return created


@pytest.mark.django_db
class TestDecisionListFiltersAPI:
    def test_list_requires_authentication(self, anonymous_client):
        response = anonymous_client.get("/api/v1/decisions/?status=failed")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_filter_by_status_csv(self, api_client, seeded_decisions):
        response = api_client.get("/api/v1/decisions/?status=failed,pending")

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        statuses = {item["status"] for item in payload}
        assert statuses == {DecisionStatus.FAILED, DecisionStatus.PENDING}

    def test_filter_by_status_is_case_insensitive(self, api_client, api_user):
        user_id = str(api_user.id)
        Decision.objects.create(
            title="Legacy completed",
            description="legacy mixed-case status record",
            status="Completed",
            created_by=user_id,
            metadata={},
        )

        response = api_client.get("/api/v1/decisions/?status=completed")

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        ids = {item["title"] for item in payload}
        assert "Legacy completed" in ids

    def test_filter_by_search_query(self, api_client, seeded_decisions):
        response = api_client.get("/api/v1/decisions/?q=fraud")

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert len(payload) == 1
        assert payload[0]["title"] == "Fraud escalation review"

    def test_filter_by_date_range(self, api_client, seeded_decisions):
        now = timezone.now()
        from_value = (now - dt.timedelta(hours=2)).isoformat()
        to_value = (now + dt.timedelta(minutes=1)).isoformat()

        response = api_client.get(
            "/api/v1/decisions/",
            {"from": from_value, "to": to_value},
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert len(payload) >= 1
        for item in payload:
            updated_at = dt.datetime.fromisoformat(
                item["updated_at"].replace("Z", "+00:00")
            )
            assert updated_at >= dt.datetime.fromisoformat(
                from_value.replace("Z", "+00:00")
            )
            assert updated_at <= dt.datetime.fromisoformat(
                to_value.replace("Z", "+00:00")
            )

    def test_combined_filters(self, api_client, seeded_decisions):
        response = api_client.get("/api/v1/decisions/?status=failed&q=fraud")

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert len(payload) == 1
        assert payload[0]["status"] == DecisionStatus.FAILED
        assert "fraud" in payload[0]["title"].lower()

    def test_limit_offset_pagination_is_stable(self, api_client, seeded_decisions):
        page_one = api_client.get("/api/v1/decisions/?limit=2&offset=0")
        page_two = api_client.get("/api/v1/decisions/?limit=2&offset=2")
        full = api_client.get("/api/v1/decisions/")

        assert page_one.status_code == status.HTTP_200_OK
        assert page_two.status_code == status.HTTP_200_OK
        assert full.status_code == status.HTTP_200_OK

        page_one_ids = [item["id"] for item in page_one.json()]
        page_two_ids = [item["id"] for item in page_two.json()]
        full_ids = [item["id"] for item in full.json()]

        assert len(page_one_ids) == 2
        assert len(page_two_ids) == 2
        assert set(page_one_ids).isdisjoint(set(page_two_ids))
        assert page_one_ids + page_two_ids == full_ids[:4]

    def test_invalid_status_filter_returns_400(self, api_client, seeded_decisions):
        response = api_client.get("/api/v1/decisions/?status=unknown")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_limit_returns_400(self, api_client, seeded_decisions):
        response = api_client.get("/api/v1/decisions/?limit=bad")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_date_returns_400(self, api_client, seeded_decisions):
        response = api_client.get("/api/v1/decisions/?from=nope")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
