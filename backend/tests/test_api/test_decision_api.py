"""
Tests for Decision API endpoints.

Follows TDD: Tests are written before implementation.

Endpoints tested:
- POST /api/v1/decisions/ - Create decision
- POST /api/v1/decisions/{id}/submit/ - Submit decision
- GET /api/v1/decisions/{id}/ - Retrieve decision
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from decisions.models import AuditAction, AuditLog, Decision, DecisionStatus


@pytest.fixture
def api_user(django_user_model):
    """Create authenticated API user."""
    return django_user_model.objects.create_user(
        username="api-user",
        email="api-user@example.com",
        password="pass1234",
    )


@pytest.fixture
def api_client(api_user):
    """Create authenticated DRF API client."""
    client = APIClient()
    client.force_authenticate(user=api_user)
    return client


@pytest.fixture
def anonymous_client():
    """Create unauthenticated DRF API client."""
    return APIClient()


@pytest.fixture
def decision_payload():
    """Valid decision creation payload."""
    return {
        "title": "Loan Application #12345",
        "description": "Process loan application for customer",
        "priority": 5,
        "metadata": {
            "customer_id": "cust_123",
            "amount": 50000,
            "product": "personal_loan",
        },
    }


@pytest.mark.django_db
class TestCreateDecision:
    """Test POST /api/v1/decisions/ endpoint."""

    def test_create_decision_returns_201(self, api_client, decision_payload):
        """
        Should return 201 Created on successful decision creation.
        """
        response = api_client.post(
            "/api/v1/decisions/", decision_payload, format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_create_decision_returns_uuid(self, api_client, decision_payload):
        """
        Should return UUID in response.
        """
        response = api_client.post(
            "/api/v1/decisions/", decision_payload, format="json"
        )
        data = response.json()

        assert "id" in data
        assert uuid.UUID(data["id"])

    def test_create_decision_returns_correct_fields(self, api_client, decision_payload):
        """
        Should return all required fields in response.
        """
        response = api_client.post(
            "/api/v1/decisions/", decision_payload, format="json"
        )
        data = response.json()

        assert data["title"] == decision_payload["title"]
        assert data["description"] == decision_payload["description"]
        assert data["priority"] == decision_payload["priority"]
        assert data["metadata"] == decision_payload["metadata"]
        assert data["status"] == DecisionStatus.DRAFT

    def test_create_decision_saves_to_database(
        self, api_client, decision_payload, api_user
    ):
        """
        Should persist decision to database.
        """
        response = api_client.post(
            "/api/v1/decisions/", decision_payload, format="json"
        )
        data = response.json()

        decision = Decision.objects.get(id=data["id"])
        assert decision.title == decision_payload["title"]
        assert decision.status == DecisionStatus.DRAFT
        assert decision.created_by == str(api_user.id)

    def test_create_decision_default_status_is_draft(
        self, api_client, decision_payload
    ):
        """
        Should set status to 'draft' by default.
        """
        response = api_client.post(
            "/api/v1/decisions/", decision_payload, format="json"
        )
        data = response.json()

        assert data["status"] == "draft"

    def test_create_decision_default_priority_is_zero(self, api_client):
        """
        Should set priority to 0 if not provided.
        """
        payload = {"title": "Test Decision", "description": "Test"}
        response = api_client.post("/api/v1/decisions/", payload, format="json")
        data = response.json()

        assert data["priority"] == 0

    def test_create_decision_default_metadata_is_empty(self, api_client):
        """
        Should set metadata to empty dict if not provided.
        """
        payload = {"title": "Test Decision", "description": "Test"}
        response = api_client.post("/api/v1/decisions/", payload, format="json")
        data = response.json()

        assert data["metadata"] == {}

    def test_create_decision_with_invalid_priority_returns_400(
        self, api_client, decision_payload
    ):
        """
        Should return 400 Bad Request for invalid priority.
        """
        decision_payload["priority"] = 15  # Out of range

        response = api_client.post(
            "/api/v1/decisions/", decision_payload, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_decision_without_title_returns_400(self, api_client):
        """
        Should return 400 Bad Request when title is missing.
        """
        payload = {"description": "Test"}
        response = api_client.post("/api/v1/decisions/", payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "title" in response.json()

    def test_create_decision_without_description_returns_400(self, api_client):
        """
        Should return 400 Bad Request when description is missing.
        """
        payload = {"title": "Test"}
        response = api_client.post("/api/v1/decisions/", payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "description" in response.json()

    def test_create_decision_creates_audit_log(self, api_client, decision_payload):
        """
        Should create an audit log entry when decision is created.
        """
        response = api_client.post(
            "/api/v1/decisions/", decision_payload, format="json"
        )
        data = response.json()

        audit_log = AuditLog.objects.filter(
            entity_type="decision", entity_id=data["id"], action=AuditAction.CREATE
        ).first()

        assert audit_log is not None
        assert audit_log.actor_type == "api"

    def test_create_decision_audit_log_contains_state(
        self, api_client, decision_payload
    ):
        """
        Audit log should contain the created state.
        """
        response = api_client.post(
            "/api/v1/decisions/", decision_payload, format="json"
        )
        data = response.json()

        audit_log = AuditLog.objects.filter(
            entity_type="decision", entity_id=data["id"], action=AuditAction.CREATE
        ).first()

        assert audit_log.current_state is not None
        assert audit_log.current_state["status"] == "draft"
        assert audit_log.current_state["title"] == decision_payload["title"]


@pytest.mark.django_db
class TestSubmitDecision:
    """Test POST /api/v1/decisions/{id}/submit/ endpoint."""

    @pytest.fixture
    def draft_decision(self, decision_payload, api_user):
        """Create a draft decision for testing."""
        return Decision.objects.create(
            title=decision_payload["title"],
            description=decision_payload["description"],
            priority=decision_payload["priority"],
            metadata=decision_payload["metadata"],
            created_by=str(api_user.id),
            status=DecisionStatus.DRAFT,
        )

    @pytest.fixture
    def other_user(self, django_user_model):
        return django_user_model.objects.create_user(
            username="other-user",
            email="other-user@example.com",
            password="pass1234",
        )

    @pytest.fixture
    def other_client(self, other_user):
        client = APIClient()
        client.force_authenticate(user=other_user)
        return client

    def test_submit_requires_authentication(self, anonymous_client, draft_decision):
        response = anonymous_client.post(
            f"/api/v1/decisions/{draft_decision.id}/submit/", {}, format="json"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_submit_non_owner_forbidden(self, other_client, draft_decision):
        response = other_client.post(
            f"/api/v1/decisions/{draft_decision.id}/submit/", {}, format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_submit_decision_returns_202(self, api_client, draft_decision):
        """
        Should return 202 Accepted on successful submission.
        """
        response = api_client.post(
            f"/api/v1/decisions/{draft_decision.id}/submit/", {}, format="json"
        )

        assert response.status_code == status.HTTP_202_ACCEPTED

    def test_submit_decision_changes_status_to_pending(
        self, api_client, draft_decision
    ):
        """
        Should change decision status from draft to pending.
        """
        api_client.post(
            f"/api/v1/decisions/{draft_decision.id}/submit/", {}, format="json"
        )

        draft_decision.refresh_from_db()
        assert draft_decision.status == DecisionStatus.PENDING

    def test_submit_decision_sets_workflow_started_at(self, api_client, draft_decision):
        """
        Should set workflow_started_at timestamp.
        """
        from django.utils import timezone

        before = timezone.now()
        api_client.post(
            f"/api/v1/decisions/{draft_decision.id}/submit/", {}, format="json"
        )
        after = timezone.now()

        draft_decision.refresh_from_db()
        assert draft_decision.workflow_started_at is not None
        assert before <= draft_decision.workflow_started_at <= after

    def test_submit_decision_publishes_to_queue(self, api_client, draft_decision):
        """
        Should publish message to RabbitMQ decision_queue.
        """
        with patch("decisions.services.publish_decision") as mock_publish:
            response = api_client.post(
                f"/api/v1/decisions/{draft_decision.id}/submit/", {}, format="json"
            )

            assert response.status_code == status.HTTP_202_ACCEPTED
            mock_publish.assert_called_once_with(str(draft_decision.id))

    def test_submit_non_draft_decision_returns_400(
        self, api_client, decision_payload, api_user
    ):
        """
        Should return 400 Bad Request if decision is not in draft status.
        """
        decision = Decision.objects.create(
            title=decision_payload["title"],
            description=decision_payload["description"],
            created_by=str(api_user.id),
            status=DecisionStatus.PENDING,  # Already pending
        )

        response = api_client.post(
            f"/api/v1/decisions/{decision.id}/submit/", {}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "status" in response.json()

    def test_submit_nonexistent_decision_returns_404(self, api_client):
        """
        Should return 404 Not Found for nonexistent decision.
        """
        nonexistent_id = uuid.uuid4()

        response = api_client.post(
            f"/api/v1/decisions/{nonexistent_id}/submit/", {}, format="json"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_submit_decision_creates_audit_log(self, api_client, draft_decision):
        """
        Should create an audit log entry when decision is submitted.
        """
        api_client.post(
            f"/api/v1/decisions/{draft_decision.id}/submit/", {}, format="json"
        )

        audit_log = AuditLog.objects.filter(
            entity_type="decision",
            entity_id=draft_decision.id,
            action=AuditAction.SUBMIT,
        ).first()

        assert audit_log is not None

    def test_submit_decision_audit_log_contains_state_change(
        self, api_client, draft_decision
    ):
        """
        Audit log should contain previous and current state.
        """
        api_client.post(
            f"/api/v1/decisions/{draft_decision.id}/submit/", {}, format="json"
        )

        audit_log = AuditLog.objects.filter(
            entity_type="decision",
            entity_id=draft_decision.id,
            action=AuditAction.SUBMIT,
        ).first()

        assert audit_log.previous_state is not None
        assert audit_log.previous_state["status"] == "draft"
        assert audit_log.current_state is not None
        assert audit_log.current_state["status"] == "pending"


@pytest.mark.django_db
class TestRetrieveDecision:
    """Test GET /api/v1/decisions/{id}/ endpoint."""

    @pytest.fixture
    def created_decision(self, decision_payload, api_user):
        """Create a decision for testing."""
        return Decision.objects.create(
            title=decision_payload["title"],
            description=decision_payload["description"],
            priority=decision_payload["priority"],
            metadata=decision_payload["metadata"],
            created_by=str(api_user.id),
        )

    @pytest.fixture
    def other_user(self, django_user_model):
        return django_user_model.objects.create_user(
            username="other-user",
            email="other-user@example.com",
            password="pass1234",
        )

    @pytest.fixture
    def other_client(self, other_user):
        client = APIClient()
        client.force_authenticate(user=other_user)
        return client

    def test_retrieve_decision_requires_authentication(
        self, anonymous_client, created_decision
    ):
        response = anonymous_client.get(f"/api/v1/decisions/{created_decision.id}/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_decision_non_owner_forbidden(
        self, other_client, created_decision
    ):
        response = other_client.get(f"/api/v1/decisions/{created_decision.id}/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_decision_returns_200(self, api_client, created_decision):
        """
        Should return 200 OK for existing decision.
        """
        response = api_client.get(f"/api/v1/decisions/{created_decision.id}/")

        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_decision_returns_correct_data(self, api_client, created_decision):
        """
        Should return correct decision data.
        """
        response = api_client.get(f"/api/v1/decisions/{created_decision.id}/")
        data = response.json()

        assert data["id"] == str(created_decision.id)
        assert data["title"] == created_decision.title
        assert data["description"] == created_decision.description
        assert data["priority"] == created_decision.priority
        assert data["metadata"] == created_decision.metadata
        assert data["status"] == created_decision.status

    def test_retrieve_nonexistent_decision_returns_404(self, api_client):
        """
        Should return 404 Not Found for nonexistent decision.
        """
        nonexistent_id = uuid.uuid4()

        response = api_client.get(f"/api/v1/decisions/{nonexistent_id}/")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_decision_includes_timestamps(self, api_client, created_decision):
        """
        Should include created_at and updated_at timestamps.
        """
        response = api_client.get(f"/api/v1/decisions/{created_decision.id}/")
        data = response.json()

        assert "created_at" in data
        assert "updated_at" in data

    def test_retrieve_decision_workflow_fields(self, api_client, created_decision):
        """
        Should include workflow-related fields.
        """
        response = api_client.get(f"/api/v1/decisions/{created_decision.id}/")
        data = response.json()

        assert "workflow_started_at" in data
        assert "workflow_completed_at" in data
        assert "agent_result" in data
        assert "agent_error" in data


@pytest.mark.django_db
class TestDecisionStateTransitions:
    """Test decision state transition validation."""

    def test_cannot_submit_completed_decision(
        self, api_client, decision_payload, api_user
    ):
        """
        Should not allow submitting a completed decision.
        """
        decision = Decision.objects.create(
            title=decision_payload["title"],
            description=decision_payload["description"],
            created_by=str(api_user.id),
            status=DecisionStatus.COMPLETED,
        )

        response = api_client.post(
            f"/api/v1/decisions/{decision.id}/submit/", {}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_submit_failed_decision(
        self, api_client, decision_payload, api_user
    ):
        """
        Should not allow submitting a failed decision.
        """
        decision = Decision.objects.create(
            title=decision_payload["title"],
            description=decision_payload["description"],
            created_by=str(api_user.id),
            status=DecisionStatus.FAILED,
        )

        response = api_client.post(
            f"/api/v1/decisions/{decision.id}/submit/", {}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_submit_processing_decision(
        self, api_client, decision_payload, api_user
    ):
        """
        Should not allow submitting a decision already being processed.
        """
        decision = Decision.objects.create(
            title=decision_payload["title"],
            description=decision_payload["description"],
            created_by=str(api_user.id),
            status=DecisionStatus.PROCESSING,
        )

        response = api_client.post(
            f"/api/v1/decisions/{decision.id}/submit/", {}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_decision_requires_authentication(
        self, anonymous_client, decision_payload
    ):
        """Should reject anonymous create requests."""
        response = anonymous_client.post(
            "/api/v1/decisions/", decision_payload, format="json"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestListDecisions:
    """Test GET /api/v1/decisions/ endpoint."""

    @pytest.fixture
    def staff_user(self, django_user_model):
        return django_user_model.objects.create_user(
            username="staff-user",
            email="staff@example.com",
            password="pass1234",
            is_staff=True,
        )

    @pytest.fixture
    def staff_client(self, staff_user):
        client = APIClient()
        client.force_authenticate(user=staff_user)
        return client

    def test_list_requires_authentication(self, anonymous_client):
        response = anonymous_client.get("/api/v1/decisions/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_owner_only_sees_owned_decisions(self, api_client, api_user):
        Decision.objects.create(
            title="Owned",
            description="owned decision",
            created_by=str(api_user.id),
            status=DecisionStatus.DRAFT,
        )
        Decision.objects.create(
            title="Not Owned",
            description="other decision",
            created_by="someone-else",
            status=DecisionStatus.DRAFT,
        )

        response = api_client.get("/api/v1/decisions/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Owned"

    def test_staff_sees_all_decisions(self, staff_client):
        Decision.objects.create(
            title="Decision A",
            description="a",
            created_by="owner-a",
            status=DecisionStatus.DRAFT,
        )
        Decision.objects.create(
            title="Decision B",
            description="b",
            created_by="owner-b",
            status=DecisionStatus.DRAFT,
        )

        response = staff_client.get("/api/v1/decisions/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 2
