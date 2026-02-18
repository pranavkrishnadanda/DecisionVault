"""Tests for Decision status API endpoint (Phase 2.5)."""

import uuid

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from decisions.models import Decision, DecisionStatus


@pytest.fixture
def owner_user(django_user_model):
    return django_user_model.objects.create_user(
        username="owner",
        email="owner@example.com",
        password="pass1234",
    )


@pytest.fixture
def other_user(django_user_model):
    return django_user_model.objects.create_user(
        username="other",
        email="other@example.com",
        password="pass1234",
    )


@pytest.fixture
def staff_user(django_user_model):
    return django_user_model.objects.create_user(
        username="staff",
        email="staff@example.com",
        password="pass1234",
        is_staff=True,
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
def staff_client(staff_user):
    client = APIClient()
    client.force_authenticate(user=staff_user)
    return client


@pytest.fixture
def anonymous_client():
    return APIClient()


@pytest.fixture
def owned_decision(owner_user):
    return Decision.objects.create(
        title="Status Decision",
        description="Check status endpoint",
        created_by=str(owner_user.id),
        status=DecisionStatus.PENDING,
        metadata={"source": "api"},
    )


@pytest.mark.django_db
class TestDecisionStatusEndpoint:
    def test_status_requires_authentication(self, anonymous_client, owned_decision):
        response = anonymous_client.get(f"/api/v1/decisions/{owned_decision.id}/status/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_owner_can_retrieve_status(self, owner_client, owned_decision):
        response = owner_client.get(f"/api/v1/decisions/{owned_decision.id}/status/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(owned_decision.id)
        assert data["status"] == DecisionStatus.PENDING
        assert "workflow_started_at" in data
        assert "workflow_completed_at" in data
        assert "updated_at" in data

    def test_staff_can_retrieve_any_status(self, staff_client, owned_decision):
        response = staff_client.get(f"/api/v1/decisions/{owned_decision.id}/status/")

        assert response.status_code == status.HTTP_200_OK

    def test_non_owner_is_forbidden(self, other_client, owned_decision):
        response = other_client.get(f"/api/v1/decisions/{owned_decision.id}/status/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_missing_decision_returns_404(self, owner_client):
        missing_id = uuid.uuid4()

        response = owner_client.get(f"/api/v1/decisions/{missing_id}/status/")

        assert response.status_code == status.HTTP_404_NOT_FOUND
