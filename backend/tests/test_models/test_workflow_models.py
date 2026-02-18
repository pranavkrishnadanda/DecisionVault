"""
Tests for Workflow and WorkflowStep models.

Follows TDD: Tests are written before implementation.
"""

import pytest
import uuid
from django.core.exceptions import ValidationError
from django.utils import timezone

from decisions.models import Workflow, WorkflowStatus, WorkflowStep, StepStatus


@pytest.mark.django_db
class TestWorkflowModel:
    """Test Workflow model structure and behavior."""

    def test_create_workflow_with_required_fields(self, decision_data, workflow_data):
        """
        Should create a workflow with required fields.
        
        Required fields: decision, status
        """
        from decisions.models import Decision
        
        decision = Decision.objects.create(
            title=decision_data["title"],
            description=decision_data["description"],
            created_by=decision_data["created_by"]
        )
        
        workflow = Workflow.objects.create(
            decision=decision,
            status=workflow_data.get("status", "pending")
        )
        
        assert workflow.id is not None
        assert isinstance(workflow.id, uuid.UUID)
        assert workflow.decision == decision
        assert workflow.status == WorkflowStatus.PENDING

    def test_workflow_default_status_is_pending(self, decision_data):
        """
        Should set status to 'pending' by default.
        """
        from decisions.models import Decision
        
        decision = Decision.objects.create(
            title="Test",
            description="Test",
            created_by="user_1"
        )
        
        workflow = Workflow.objects.create(decision=decision)
        
        assert workflow.status == WorkflowStatus.PENDING

    def test_workflow_name_is_optional(self, decision_data):
        """
        Should allow name to be null/blank.
        """
        from decisions.models import Decision
        
        decision = Decision.objects.create(
            title="Test",
            description="Test",
            created_by="user_1"
        )
        
        workflow = Workflow.objects.create(
            decision=decision,
            name=None
        )
        
        assert workflow.name is None

    def test_workflow_description_is_optional(self, decision_data):
        """
        Should allow description to be blank.
        """
        from decisions.models import Decision
        
        decision = Decision.objects.create(
            title="Test",
            description="Test",
            created_by="user_1"
        )
        
        workflow = Workflow.objects.create(
            decision=decision,
            description=""
        )
        
        assert workflow.description == ""

    def test_workflow_timeout_default_is_300(self, decision_data):
        """
        Should set timeout_sec to 300 by default.
        """
        from decisions.models import Decision
        
        decision = Decision.objects.create(
            title="Test",
            description="Test",
            created_by="user_1"
        )
        
        workflow = Workflow.objects.create(decision=decision)
        
        assert workflow.timeout_sec == 300

    def test_workflow_max_retries_default_is_3(self, decision_data):
        """
        Should set max_retries to 3 by default.
        """
        from decisions.models import Decision
        
        decision = Decision.objects.create(
            title="Test",
            description="Test",
            created_by="user_1"
        )
        
        workflow = Workflow.objects.create(decision=decision)
        
        assert workflow.max_retries == 3

    def test_workflow_created_at_is_auto_set(self, decision_data):
        """
        Should automatically set created_at on save.
        """
        from decisions.models import Decision
        
        decision = Decision.objects.create(
            title="Test",
            description="Test",
            created_by="user_1"
        )
        
        before = timezone.now()
        workflow = Workflow.objects.create(decision=decision)
        after = timezone.now()
        
        assert workflow.created_at is not None
        assert before <= workflow.created_at <= after

    def test_workflow_updated_at_is_auto_set(self, decision_data):
        """
        Should automatically set updated_at on save and update on change.
        """
        from decisions.models import Decision
        
        decision = Decision.objects.create(
            title="Test",
            description="Test",
            created_by="user_1"
        )
        
        workflow = Workflow.objects.create(decision=decision)
        initial_updated = workflow.updated_at
        
        workflow.name = "Updated Name"
        workflow.save()
        workflow.refresh_from_db()
        
        assert workflow.updated_at >= initial_updated

    def test_workflow_started_at_nullable(self, decision_data):
        """
        Should allow started_at to be null initially.
        """
        from decisions.models import Decision
        
        decision = Decision.objects.create(
            title="Test",
            description="Test",
            created_by="user_1"
        )
        
        workflow = Workflow.objects.create(decision=decision)
        
        assert workflow.started_at is None

    def test_workflow_completed_at_nullable(self, decision_data):
        """
        Should allow completed_at to be null initially.
        """
        from decisions.models import Decision
        
        decision = Decision.objects.create(
            title="Test",
            description="Test",
            created_by="user_1"
        )
        
        workflow = Workflow.objects.create(decision=decision)
        
        assert workflow.completed_at is None

    def test_workflow_str_representation(self, decision_data):
        """
        Should return name or decision title as string representation.
        """
        from decisions.models import Decision
        
        decision = Decision.objects.create(
            title="Test Decision",
            description="Test",
            created_by="user_1"
        )
        
        workflow = Workflow.objects.create(
            decision=decision,
            name="Test Workflow"
        )
        
        assert str(workflow) == "Test Workflow"

    def test_workflow_str_without_name(self, decision_data):
        """
        Should return decision title when name is not set.
        """
        from decisions.models import Decision
        
        decision = Decision.objects.create(
            title="Test Decision",
            description="Test",
            created_by="user_1"
        )
        
        workflow = Workflow.objects.create(decision=decision, name=None)
        
        assert str(workflow) == "Test Decision"

    def test_workflow_cascade_delete_decision(self, decision_data):
        """
        Should delete workflow when decision is deleted.
        """
        from decisions.models import Decision
        
        decision = Decision.objects.create(
            title="Test",
            description="Test",
            created_by="user_1"
        )
        
        workflow = Workflow.objects.create(decision=decision)
        workflow_id = workflow.id
        
        decision.delete()
        
        assert not Workflow.objects.filter(id=workflow_id).exists()


@pytest.mark.django_db
class TestWorkflowStatusTransitions:
    """Test Workflow status transition logic."""

    def test_transition_pending_to_running(self, decision_data):
        """
        Should allow transition from pending to running.
        """
        from decisions.models import Decision
        
        decision = Decision.objects.create(
            title="Test",
            description="Test",
            created_by="user_1"
        )
        
        workflow = Workflow.objects.create(decision=decision)
        workflow.status = WorkflowStatus.RUNNING
        workflow.save()
        workflow.refresh_from_db()
        
        assert workflow.status == WorkflowStatus.RUNNING

    def test_transition_running_to_completed(self, decision_data):
        """
        Should allow transition from running to completed.
        """
        from decisions.models import Decision
        
        decision = Decision.objects.create(
            title="Test",
            description="Test",
            created_by="user_1"
        )
        
        workflow = Workflow.objects.create(
            decision=decision,
            status=WorkflowStatus.RUNNING
        )
        workflow.status = WorkflowStatus.COMPLETED
        workflow.save()
        workflow.refresh_from_db()
        
        assert workflow.status == WorkflowStatus.COMPLETED

    def test_transition_running_to_failed(self, decision_data):
        """
        Should allow transition from running to failed.
        """
        from decisions.models import Decision
        
        decision = Decision.objects.create(
            title="Test",
            description="Test",
            created_by="user_1"
        )
        
        workflow = Workflow.objects.create(
            decision=decision,
            status=WorkflowStatus.RUNNING
        )
        workflow.status = WorkflowStatus.FAILED
        workflow.save()
        workflow.refresh_from_db()
        
        assert workflow.status == WorkflowStatus.FAILED

    def test_status_choices_are_valid(self):
        """
        Should have valid status choices defined.
        """
        expected_statuses = ["pending", "running", "completed", "failed", "cancelled"]
        actual_statuses = [choice[0] for choice in WorkflowStatus.choices]
        
        assert sorted(actual_statuses) == sorted(expected_statuses)


@pytest.mark.django_db
class TestWorkflowStepModel:
    """Test WorkflowStep model structure and behavior."""

    def test_create_step_with_required_fields(self, decision_data, workflow_step_data):
        """
        Should create a step with required fields.
        
        Required fields: workflow, step_number, agent_type, action
        """
        from decisions.models import Decision, Workflow
        
        decision = Decision.objects.create(
            title=decision_data["title"],
            description=decision_data["description"],
            created_by=decision_data["created_by"]
        )
        
        workflow = Workflow.objects.create(decision=decision)
        
        step = WorkflowStep.objects.create(
            workflow=workflow,
            step_number=workflow_step_data["step_number"],
            agent_type=workflow_step_data["agent_type"],
            action=workflow_step_data["action"]
        )
        
        assert step.id is not None
        assert isinstance(step.id, uuid.UUID)
        assert step.workflow == workflow
        assert step.step_number == 1
        assert step.agent_type == "schema_validator"
        assert step.action == "validate_schema"

    def test_step_default_status_is_pending(self, decision_data):
        """
        Should set status to 'pending' by default.
        """
        from decisions.models import Decision, Workflow
        
        decision = Decision.objects.create(
            title="Test",
            description="Test",
            created_by="user_1"
        )
        workflow = Workflow.objects.create(decision=decision)
        
        step = WorkflowStep.objects.create(
            workflow=workflow,
            step_number=1,
            agent_type="validator",
            action="validate"
        )
        
        assert step.status == StepStatus.PENDING

    def test_step_retry_count_default_is_zero(self, decision_data):
        """
        Should set retry_count to 0 by default.
        """
        from decisions.models import Decision, Workflow
        
        decision = Decision.objects.create(
            title="Test",
            description="Test",
            created_by="user_1"
        )
        workflow = Workflow.objects.create(decision=decision)
        
        step = WorkflowStep.objects.create(
            workflow=workflow,
            step_number=1,
            agent_type="validator",
            action="validate"
        )
        
        assert step.retry_count == 0

    def test_step_max_retries_default_is_3(self, decision_data):
        """
        Should set max_retries to 3 by default.
        """
        from decisions.models import Decision, Workflow
        
        decision = Decision.objects.create(
            title="Test",
            description="Test",
            created_by="user_1"
        )
        workflow = Workflow.objects.create(decision=decision)
        
        step = WorkflowStep.objects.create(
            workflow=workflow,
            step_number=1,
            agent_type="validator",
            action="validate"
        )
        
        assert step.max_retries == 3

    def test_step_timeout_default_is_300(self, decision_data):
        """
        Should set timeout_sec to 300 by default.
        """
        from decisions.models import Decision, Workflow
        
        decision = Decision.objects.create(
            title="Test",
            description="Test",
            created_by="user_1"
        )
        workflow = Workflow.objects.create(decision=decision)
        
        step = WorkflowStep.objects.create(
            workflow=workflow,
            step_number=1,
            agent_type="validator",
            action="validate"
        )
        
        assert step.timeout_sec == 300

    def test_step_result_default_is_empty_dict(self, decision_data):
        """
        Should initialize result as empty dict by default.
        """
        from decisions.models import Decision, Workflow
        
        decision = Decision.objects.create(
            title="Test",
            description="Test",
            created_by="user_1"
        )
        workflow = Workflow.objects.create(decision=decision)
        
        step = WorkflowStep.objects.create(
            workflow=workflow,
            step_number=1,
            agent_type="validator",
            action="validate"
        )
        
        assert step.result == {}

    def test_step_error_default_is_empty_dict(self, decision_data):
        """
        Should initialize error as empty dict by default.
        """
        from decisions.models import Decision, Workflow
        
        decision = Decision.objects.create(
            title="Test",
            description="Test",
            created_by="user_1"
        )
        workflow = Workflow.objects.create(decision=decision)
        
        step = WorkflowStep.objects.create(
            workflow=workflow,
            step_number=1,
            agent_type="validator",
            action="validate"
        )
        
        assert step.error == {}

    def test_step_started_at_nullable(self, decision_data):
        """
        Should allow started_at to be null initially.
        """
        from decisions.models import Decision, Workflow
        
        decision = Decision.objects.create(
            title="Test",
            description="Test",
            created_by="user_1"
        )
        workflow = Workflow.objects.create(decision=decision)
        
        step = WorkflowStep.objects.create(
            workflow=workflow,
            step_number=1,
            agent_type="validator",
            action="validate"
        )
        
        assert step.started_at is None

    def test_step_completed_at_nullable(self, decision_data):
        """
        Should allow completed_at to be null initially.
        """
        from decisions.models import Decision, Workflow
        
        decision = Decision.objects.create(
            title="Test",
            description="Test",
            created_by="user_1"
        )
        workflow = Workflow.objects.create(decision=decision)
        
        step = WorkflowStep.objects.create(
            workflow=workflow,
            step_number=1,
            agent_type="validator",
            action="validate"
        )
        
        assert step.completed_at is None

    def test_step_str_representation(self, decision_data):
        """
        Should return step description as string representation.
        """
        from decisions.models import Decision, Workflow
        
        decision = Decision.objects.create(
            title="Test",
            description="Test",
            created_by="user_1"
        )
        workflow = Workflow.objects.create(decision=decision)
        
        step = WorkflowStep.objects.create(
            workflow=workflow,
            step_number=1,
            agent_type="schema_validator",
            action="validate_schema"
        )
        
        assert str(step) == "Step 1: validate_schema"

    def test_step_cascade_delete_workflow(self, decision_data):
        """
        Should delete step when workflow is deleted.
        """
        from decisions.models import Decision, Workflow
        
        decision = Decision.objects.create(
            title="Test",
            description="Test",
            created_by="user_1"
        )
        workflow = Workflow.objects.create(decision=decision)
        
        step = WorkflowStep.objects.create(
            workflow=workflow,
            step_number=1,
            agent_type="validator",
            action="validate"
        )
        step_id = step.id
        
        workflow.delete()
        
        assert not WorkflowStep.objects.filter(id=step_id).exists()


@pytest.mark.django_db
class TestStepStatusTransitions:
    """Test WorkflowStep status transition logic."""

    def test_transition_pending_to_queued(self, decision_data):
        """
        Should allow transition from pending to queued.
        """
        from decisions.models import Decision, Workflow
        
        decision = Decision.objects.create(
            title="Test",
            description="Test",
            created_by="user_1"
        )
        workflow = Workflow.objects.create(decision=decision)
        
        step = WorkflowStep.objects.create(
            workflow=workflow,
            step_number=1,
            agent_type="validator",
            action="validate"
        )
        step.status = StepStatus.QUEUED
        step.save()
        
        assert step.status == StepStatus.QUEUED

    def test_transition_queued_to_running(self, decision_data):
        """
        Should allow transition from queued to running.
        """
        from decisions.models import Decision, Workflow
        
        decision = Decision.objects.create(
            title="Test",
            description="Test",
            created_by="user_1"
        )
        workflow = Workflow.objects.create(decision=decision)
        
        step = WorkflowStep.objects.create(
            workflow=workflow,
            step_number=1,
            agent_type="validator",
            action="validate",
            status=StepStatus.QUEUED
        )
        step.status = StepStatus.RUNNING
        step.save()
        
        assert step.status == StepStatus.RUNNING

    def test_transition_running_to_completed(self, decision_data):
        """
        Should allow transition from running to completed.
        """
        from decisions.models import Decision, Workflow
        
        decision = Decision.objects.create(
            title="Test",
            description="Test",
            created_by="user_1"
        )
        workflow = Workflow.objects.create(decision=decision)
        
        step = WorkflowStep.objects.create(
            workflow=workflow,
            step_number=1,
            agent_type="validator",
            action="validate",
            status=StepStatus.RUNNING
        )
        step.status = StepStatus.COMPLETED
        step.save()
        
        assert step.status == StepStatus.COMPLETED

    def test_transition_running_to_failed(self, decision_data):
        """
        Should allow transition from running to failed.
        """
        from decisions.models import Decision, Workflow
        
        decision = Decision.objects.create(
            title="Test",
            description="Test",
            created_by="user_1"
        )
        workflow = Workflow.objects.create(decision=decision)
        
        step = WorkflowStep.objects.create(
            workflow=workflow,
            step_number=1,
            agent_type="validator",
            action="validate",
            status=StepStatus.RUNNING
        )
        step.status = StepStatus.FAILED
        step.save()
        
        assert step.status == StepStatus.FAILED

    def test_status_choices_are_valid(self):
        """
        Should have valid status choices defined.
        """
        expected_statuses = [
            "pending", "queued", "running", 
            "completed", "failed", "retrying", "skipped"
        ]
        actual_statuses = [choice[0] for choice in StepStatus.choices]
        
        assert sorted(actual_statuses) == sorted(expected_statuses)
