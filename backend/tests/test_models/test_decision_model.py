"""
Tests for Decision model.

Follows TDD: Tests are written before implementation.
"""

import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone

from decisions.models import Decision, DecisionStatus


@pytest.mark.django_db
class TestDecisionModel:
    """Test Decision model structure and behavior."""

    def test_create_decision_with_required_fields(self, decision_data):
        """
        Should create a decision with only required fields.

        Required fields: title, description, created_by
        """
        decision = Decision.objects.create(
            title=decision_data["title"],
            description=decision_data["description"],
            created_by=decision_data["created_by"],
        )

        assert decision.id is not None
        assert isinstance(decision.id, uuid.UUID)
        assert decision.title == decision_data["title"]
        assert decision.description == decision_data["description"]
        assert decision.created_by == decision_data["created_by"]

    def test_decision_default_status_is_draft(self, decision_data):
        """
        Should set status to 'draft' by default.
        """
        decision = Decision.objects.create(
            title=decision_data["title"],
            description=decision_data["description"],
            created_by=decision_data["created_by"],
        )

        assert decision.status == DecisionStatus.DRAFT

    def test_decision_default_priority_is_zero(self, decision_data):
        """
        Should set priority to 0 by default.
        """
        decision = Decision.objects.create(
            title=decision_data["title"],
            description=decision_data["description"],
            created_by=decision_data["created_by"],
        )

        assert decision.priority == 0

    def test_decision_priority_range_validation(self, decision_data):
        """
        Should validate priority is between -10 and 10.
        """
        # Valid priorities
        decision = Decision.objects.create(
            title=decision_data["title"],
            description=decision_data["description"],
            created_by=decision_data["created_by"],
            priority=-10,
        )
        assert decision.priority == -10

        decision = Decision.objects.create(
            title="Test 2", description="Test", created_by="user_1", priority=10
        )
        assert decision.priority == 10

    def test_decision_metadata_default_is_empty_dict(self, decision_data):
        """
        Should initialize metadata as empty dict by default.
        """
        decision = Decision.objects.create(
            title=decision_data["title"],
            description=decision_data["description"],
            created_by=decision_data["created_by"],
        )

        assert decision.metadata == {}

    def test_decision_metadata_stores_json(self, decision_data):
        """
        Should store arbitrary JSON in metadata field.
        """
        metadata = {
            "customer_id": "cust_123",
            "amount": 50000,
            "nested": {"key": "value"},
            "list": [1, 2, 3],
        }

        decision = Decision.objects.create(
            title=decision_data["title"],
            description=decision_data["description"],
            created_by=decision_data["created_by"],
            metadata=metadata,
        )

        assert decision.metadata == metadata

    def test_decision_created_at_is_auto_set(self, decision_data):
        """
        Should automatically set created_at on save.
        """
        before = timezone.now()
        decision = Decision.objects.create(
            title=decision_data["title"],
            description=decision_data["description"],
            created_by=decision_data["created_by"],
        )
        after = timezone.now()

        assert decision.created_at is not None
        assert before <= decision.created_at <= after

    def test_decision_updated_at_is_auto_set(self, decision_data):
        """
        Should automatically set updated_at on save and update on change.
        """
        decision = Decision.objects.create(
            title=decision_data["title"],
            description=decision_data["description"],
            created_by=decision_data["created_by"],
        )

        initial_updated = decision.updated_at

        # Modify and save
        decision.title = "Updated Title"
        decision.save()
        decision.refresh_from_db()

        assert decision.updated_at >= initial_updated

    def test_decision_str_representation(self, decision_data):
        """
        Should return title as string representation.
        """
        decision = Decision.objects.create(
            title=decision_data["title"],
            description=decision_data["description"],
            created_by=decision_data["created_by"],
        )

        assert str(decision) == decision_data["title"]

    def test_decision_workflow_started_at_nullable(self, decision_data):
        """
        Should allow workflow_started_at to be null initially.
        """
        decision = Decision.objects.create(
            title=decision_data["title"],
            description=decision_data["description"],
            created_by=decision_data["created_by"],
        )

        assert decision.workflow_started_at is None

    def test_decision_workflow_completed_at_nullable(self, decision_data):
        """
        Should allow workflow_completed_at to be null initially.
        """
        decision = Decision.objects.create(
            title=decision_data["title"],
            description=decision_data["description"],
            created_by=decision_data["created_by"],
        )

        assert decision.workflow_completed_at is None

    def test_decision_agent_result_default_is_empty_dict(self, decision_data):
        """
        Should initialize agent_result as empty dict by default.
        """
        decision = Decision.objects.create(
            title=decision_data["title"],
            description=decision_data["description"],
            created_by=decision_data["created_by"],
        )

        assert decision.agent_result == {}

    def test_decision_agent_error_default_is_empty_string(self, decision_data):
        """
        Should initialize agent_error as empty string by default.
        """
        decision = Decision.objects.create(
            title=decision_data["title"],
            description=decision_data["description"],
            created_by=decision_data["created_by"],
        )

        assert decision.agent_error == ""


@pytest.mark.django_db
class TestDecisionStatusTransitions:
    """Test Decision status transition logic."""

    def test_transition_draft_to_pending(self, decision_data):
        """
        Should allow transition from draft to pending.
        """
        decision = Decision.objects.create(
            title=decision_data["title"],
            description=decision_data["description"],
            created_by=decision_data["created_by"],
        )

        decision.status = DecisionStatus.PENDING
        decision.save()
        decision.refresh_from_db()

        assert decision.status == DecisionStatus.PENDING

    def test_transition_pending_to_processing(self, decision_data):
        """
        Should allow transition from pending to processing.
        """
        decision = Decision.objects.create(
            title=decision_data["title"],
            description=decision_data["description"],
            created_by=decision_data["created_by"],
            status=DecisionStatus.PENDING,
        )

        decision.status = DecisionStatus.PROCESSING
        decision.save()
        decision.refresh_from_db()

        assert decision.status == DecisionStatus.PROCESSING

    def test_transition_processing_to_completed(self, decision_data):
        """
        Should allow transition from processing to completed.
        """
        decision = Decision.objects.create(
            title=decision_data["title"],
            description=decision_data["description"],
            created_by=decision_data["created_by"],
            status=DecisionStatus.PROCESSING,
        )

        decision.status = DecisionStatus.COMPLETED
        decision.save()
        decision.refresh_from_db()

        assert decision.status == DecisionStatus.COMPLETED

    def test_transition_processing_to_failed(self, decision_data):
        """
        Should allow transition from processing to failed.
        """
        decision = Decision.objects.create(
            title=decision_data["title"],
            description=decision_data["description"],
            created_by=decision_data["created_by"],
            status=DecisionStatus.PROCESSING,
        )

        decision.status = DecisionStatus.FAILED
        decision.save()
        decision.refresh_from_db()

        assert decision.status == DecisionStatus.FAILED

    def test_status_choices_are_valid(self):
        """
        Should have valid status choices defined.
        """
        expected_statuses = ["draft", "pending", "processing", "completed", "failed"]

        actual_statuses = [choice[0] for choice in DecisionStatus.choices]

        assert sorted(actual_statuses) == sorted(expected_statuses)


@pytest.mark.django_db
class TestDecisionManager:
    """Test Decision model manager and querysets."""

    def test_manager_has_custom_methods(self):
        """
        Should have custom manager methods.
        """
        assert hasattr(Decision.objects, "draft")
        assert hasattr(Decision.objects, "pending")
        assert hasattr(Decision.objects, "processing")
        assert hasattr(Decision.objects, "completed")
        assert hasattr(Decision.objects, "failed")

    def test_draft_queryset_filters_correctly(self, decision_data):
        """
        Should filter decisions by draft status.
        """
        draft_decision = Decision.objects.create(
            title="Draft Decision",
            description="Test",
            created_by="user_1",
            status=DecisionStatus.DRAFT,
        )
        Decision.objects.create(
            title="Pending Decision",
            description="Test",
            created_by="user_1",
            status=DecisionStatus.PENDING,
        )

        draft_decisions = Decision.objects.draft()

        draft_ids = {decision.id for decision in draft_decisions}
        assert draft_decision.id in draft_ids

    def test_pending_queryset_filters_correctly(self, decision_data):
        """
        Should filter decisions by pending status.
        """
        Decision.objects.create(
            title="Draft Decision",
            description="Test",
            created_by="user_1",
            status=DecisionStatus.DRAFT,
        )
        Decision.objects.create(
            title="Pending Decision",
            description="Test",
            created_by="user_1",
            status=DecisionStatus.PENDING,
        )

        pending_decisions = Decision.objects.pending()

        assert pending_decisions.count() == 1
        assert pending_decisions.first().status == DecisionStatus.PENDING

    def test_completed_queryset_filters_correctly(self, decision_data):
        """
        Should filter decisions by completed status.
        """
        Decision.objects.create(
            title="Completed Decision",
            description="Test",
            created_by="user_1",
            status=DecisionStatus.COMPLETED,
        )
        Decision.objects.create(
            title="Draft Decision",
            description="Test",
            created_by="user_1",
            status=DecisionStatus.DRAFT,
        )

        completed_decisions = Decision.objects.completed()

        assert completed_decisions.count() == 1
        assert completed_decisions.first().status == DecisionStatus.COMPLETED
