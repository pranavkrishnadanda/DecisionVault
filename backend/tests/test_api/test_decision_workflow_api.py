"""Tests for Decision workflow API endpoint (Phase 2.5)."""

import uuid

import pytest
from django.utils import timezone
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
def owned_workflow_decision(owner_user):
    started_at = timezone.now()
    completed_at = started_at + timezone.timedelta(minutes=2)

    return Decision.objects.create(
        title="Workflow Decision",
        description="Workflow endpoint contract",
        created_by=str(owner_user.id),
        status=DecisionStatus.COMPLETED,
        metadata={"source": "api"},
        workflow_started_at=started_at,
        workflow_completed_at=completed_at,
        agent_result={"valid": True, "errors": []},
        agent_error="",
    )


@pytest.mark.django_db
class TestDecisionWorkflowEndpoint:
    def test_workflow_requires_authentication(self, anonymous_client, owned_workflow_decision):
        response = anonymous_client.get(f"/api/v1/decisions/{owned_workflow_decision.id}/workflow/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_owner_can_retrieve_workflow(self, owner_client, owned_workflow_decision):
        response = owner_client.get(f"/api/v1/decisions/{owned_workflow_decision.id}/workflow/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(owned_workflow_decision.id)
        assert data["status"] == DecisionStatus.COMPLETED
        assert data["workflow_started_at"] is not None
        assert data["workflow_completed_at"] is not None
        assert data["agent_result"]["valid"] is True
        assert data["agent_error"] == ""

    def test_staff_can_retrieve_any_workflow(self, staff_client, owned_workflow_decision):
        response = staff_client.get(f"/api/v1/decisions/{owned_workflow_decision.id}/workflow/")

        assert response.status_code == status.HTTP_200_OK

    def test_non_owner_is_forbidden(self, other_client, owned_workflow_decision):
        response = other_client.get(f"/api/v1/decisions/{owned_workflow_decision.id}/workflow/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_missing_decision_returns_404(self, owner_client):
        missing_id = uuid.uuid4()

        response = owner_client.get(f"/api/v1/decisions/{missing_id}/workflow/")

        assert response.status_code == status.HTTP_404_NOT_FOUND
