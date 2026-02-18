"""Tests for worker task handlers using TDD."""

import uuid

import pytest

from decisions.models import AuditAction, AuditLog, Decision, DecisionStatus
from workers.tasks import process_decision_task


@pytest.mark.django_db
class TestProcessDecisionTask:
    def test_process_decision_task_completes_pending_decision(self):
        decision = Decision.objects.create(
            title="Loan Decision",
            description="Validate loan decision",
            created_by="user_1",
            status=DecisionStatus.PENDING,
            metadata={"source": "web"},
        )

        process_decision_task(
            {
                "type": "decision.process",
                "payload": {"decision_id": str(decision.id)},
            }
        )

        decision.refresh_from_db()
        assert decision.status == DecisionStatus.COMPLETED
        assert decision.workflow_completed_at is not None
        assert decision.agent_result["valid"] is True
        assert decision.agent_error == ""

        actions = list(
            AuditLog.objects.filter(
                entity_type="decision",
                entity_id=decision.id,
            ).values_list("action", flat=True)
        )
        assert AuditAction.PROCESSING_START in actions
        assert AuditAction.PROCESSING_COMPLETE in actions

    def test_process_decision_task_fails_when_schema_validation_fails(self):
        decision = Decision.objects.create(
            title="",
            description="Missing title content",
            created_by="user_1",
            status=DecisionStatus.PENDING,
            metadata={"source": "web"},
        )

        process_decision_task(
            {
                "type": "decision.process",
                "payload": {"decision_id": str(decision.id)},
            }
        )

        decision.refresh_from_db()
        assert decision.status == DecisionStatus.FAILED
        assert decision.workflow_completed_at is not None
        assert decision.agent_result["valid"] is False
        assert decision.agent_error != ""

        actions = list(
            AuditLog.objects.filter(
                entity_type="decision",
                entity_id=decision.id,
            ).values_list("action", flat=True)
        )
        assert AuditAction.PROCESSING_START in actions
        assert AuditAction.PROCESSING_FAILED in actions

    def test_process_decision_task_rejects_non_pending_status(self):
        decision = Decision.objects.create(
            title="Already done",
            description="Should not reprocess",
            created_by="user_1",
            status=DecisionStatus.COMPLETED,
            metadata={"source": "web"},
        )

        with pytest.raises(ValueError, match="pending"):
            process_decision_task(
                {
                    "type": "decision.process",
                    "payload": {"decision_id": str(decision.id)},
                }
            )

    def test_process_decision_task_raises_for_missing_decision(self):
        missing_id = uuid.uuid4()

        with pytest.raises(Decision.DoesNotExist):
            process_decision_task(
                {
                    "type": "decision.process",
                    "payload": {"decision_id": str(missing_id)},
                }
            )
