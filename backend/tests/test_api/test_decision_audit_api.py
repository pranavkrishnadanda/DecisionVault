"""Tests for Decision audit trail API endpoint."""

import uuid

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from decisions.models import AuditAction, AuditLog, Decision, DecisionStatus


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


@pytest.fixture
def decision_with_audit(owner_user):
    decision = Decision.objects.create(
        title="Decision With Audit",
        description="Audit trail validation",
        created_by=str(owner_user.id),
        status=DecisionStatus.PENDING,
        metadata={"source": "api"},
    )

    AuditLog.objects.create(
        entity_type="decision",
        entity_id=decision.id,
        action=AuditAction.CREATE,
        actor_type="user",
        actor_id=str(owner_user.id),
        current_state={"status": DecisionStatus.DRAFT},
        metadata={"source": "api"},
    )
    AuditLog.objects.create(
        entity_type="decision",
        entity_id=decision.id,
        action=AuditAction.SUBMIT,
        actor_type="user",
        actor_id=str(owner_user.id),
        previous_state={"status": DecisionStatus.DRAFT},
        current_state={"status": DecisionStatus.PENDING},
        metadata={"source": "api"},
    )

    return decision


@pytest.mark.django_db
class TestDecisionAuditTrailEndpoint:
    def test_audit_requires_authentication(self, anonymous_client, decision_with_audit):
        response = anonymous_client.get(
            f"/api/v1/decisions/{decision_with_audit.id}/audit/"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_owner_can_retrieve_audit_trail(self, owner_client, decision_with_audit):
        response = owner_client.get(
            f"/api/v1/decisions/{decision_with_audit.id}/audit/"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["action"] == AuditAction.CREATE
        assert data[1]["action"] == AuditAction.SUBMIT
        assert data[1]["current_state"]["status"] == DecisionStatus.PENDING

    def test_non_owner_is_forbidden(self, other_client, decision_with_audit):
        response = other_client.get(
            f"/api/v1/decisions/{decision_with_audit.id}/audit/"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_missing_decision_returns_404(self, owner_client):
        missing_id = uuid.uuid4()

        response = owner_client.get(f"/api/v1/decisions/{missing_id}/audit/")

        assert response.status_code == status.HTTP_404_NOT_FOUND
