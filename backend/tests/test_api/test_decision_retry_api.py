"""Tests for Decision retry API endpoint (Phase 2.5)."""

import uuid
from unittest.mock import patch

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
def failed_decision(owner_user):
    return Decision.objects.create(
        title="Retry me",
        description="Failed decision",
        created_by=str(owner_user.id),
        status=DecisionStatus.FAILED,
        metadata={"source": "api"},
        agent_result={"valid": False, "errors": ["bad payload"]},
        agent_error="bad payload",
    )


@pytest.mark.django_db
class TestDecisionRetryEndpoint:
    def test_retry_requires_authentication(self, anonymous_client, failed_decision):
        response = anonymous_client.post(
            f"/api/v1/decisions/{failed_decision.id}/retry/", {}, format="json"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_owner_can_retry_failed_decision(self, owner_client, failed_decision):
        with patch(
            "decisions.services.publish_decision", return_value=True
        ) as mock_publish:
            response = owner_client.post(
                f"/api/v1/decisions/{failed_decision.id}/retry/", {}, format="json"
            )

        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert data["id"] == str(failed_decision.id)
        assert data["status"] == DecisionStatus.PENDING
        assert data["message"] == "Decision queued for retry"

        failed_decision.refresh_from_db()
        assert failed_decision.status == DecisionStatus.PENDING
        assert failed_decision.workflow_started_at is not None
        assert failed_decision.workflow_completed_at is None
        assert failed_decision.agent_result == {}
        assert failed_decision.agent_error == ""

        mock_publish.assert_called_once_with(str(failed_decision.id))

        audit_log = AuditLog.objects.filter(
            entity_type="decision",
            entity_id=failed_decision.id,
            action=AuditAction.UPDATE,
            metadata__operation="retry",
        ).first()
        assert audit_log is not None
        assert audit_log.previous_state["status"] == DecisionStatus.FAILED
        assert audit_log.current_state["status"] == DecisionStatus.PENDING

    def test_staff_can_retry_failed_decision(self, staff_client, failed_decision):
        with patch("decisions.services.publish_decision", return_value=True):
            response = staff_client.post(
                f"/api/v1/decisions/{failed_decision.id}/retry/", {}, format="json"
            )

        assert response.status_code == status.HTTP_202_ACCEPTED

    def test_non_owner_not_found(self, other_client, failed_decision):
        response = other_client.post(
            f"/api/v1/decisions/{failed_decision.id}/retry/", {}, format="json"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retry_non_failed_decision_returns_400(self, owner_client, owner_user):
        pending_decision = Decision.objects.create(
            title="Not failed",
            description="Pending decision",
            created_by=str(owner_user.id),
            status=DecisionStatus.PENDING,
            metadata={"source": "api"},
        )

        response = owner_client.post(
            f"/api/v1/decisions/{pending_decision.id}/retry/", {}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "status" in response.json()

    def test_missing_decision_returns_404(self, owner_client):
        missing_id = uuid.uuid4()

        response = owner_client.post(
            f"/api/v1/decisions/{missing_id}/retry/", {}, format="json"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
