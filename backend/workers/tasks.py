"""Worker task handlers for DecisionVault."""

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction
from django.utils import timezone

from decisions.models import AuditAction, AuditLog, Decision, DecisionStatus

logger = logging.getLogger(__name__)


def validate_decision_schema(decision: Decision) -> dict[str, Any]:
    """Validate decision data against MVP v1 schema constraints."""
    errors: list[str] = []

    if not isinstance(decision.title, str) or not decision.title.strip():
        errors.append("title must be a non-empty string")

    if not isinstance(decision.description, str) or not decision.description.strip():
        errors.append("description must be a non-empty string")

    if not isinstance(decision.priority, int) or not (-10 <= decision.priority <= 10):
        errors.append("priority must be an integer between -10 and 10")

    if not isinstance(decision.metadata, dict):
        errors.append("metadata must be an object")

    return {"valid": len(errors) == 0, "errors": errors}


def _log_processing_event(
    *,
    decision: Decision,
    action: AuditAction,
    previous_status: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Persist worker processing audit events."""
    AuditLog.objects.create(
        entity_type="decision",
        entity_id=decision.id,
        action=action,
        actor_type="worker",
        actor_id="schema_validator",
        previous_state={"status": previous_status},
        current_state={"status": decision.status},
        metadata=metadata or {"source": "worker"},
    )


@transaction.atomic
def process_decision_task(message: dict[str, Any]) -> dict[str, Any]:
    """Process a decision task from RabbitMQ."""
    payload = message.get("payload", {})
    decision_id = payload.get("decision_id")

    if not decision_id:
        raise ValueError("decision_id is required in payload")

    decision = Decision.objects.select_for_update().get(id=decision_id)

    if decision.status != DecisionStatus.PENDING:
        raise ValueError("Decision must be in pending status to process")

    previous_status = decision.status
    decision.status = DecisionStatus.PROCESSING
    decision.save(update_fields=["status", "updated_at"])
    _log_processing_event(
        decision=decision,
        action=AuditAction.PROCESSING_START,
        previous_status=previous_status,
    )

    validation_result = validate_decision_schema(decision)

    terminal_previous_status = decision.status
    decision.workflow_completed_at = timezone.now()
    decision.agent_result = validation_result

    if validation_result["valid"]:
        decision.status = DecisionStatus.COMPLETED
        decision.agent_error = ""
        decision.save(
            update_fields=[
                "status",
                "workflow_completed_at",
                "agent_result",
                "agent_error",
                "updated_at",
            ]
        )
        _log_processing_event(
            decision=decision,
            action=AuditAction.PROCESSING_COMPLETE,
            previous_status=terminal_previous_status,
            metadata={"source": "worker", "result": validation_result},
        )
        logger.info("Decision %s completed by schema validator", decision.id)
        return validation_result

    decision.status = DecisionStatus.FAILED
    decision.agent_error = "; ".join(validation_result["errors"])
    decision.save(
        update_fields=[
            "status",
            "workflow_completed_at",
            "agent_result",
            "agent_error",
            "updated_at",
        ]
    )
    _log_processing_event(
        decision=decision,
        action=AuditAction.PROCESSING_FAILED,
        previous_status=terminal_previous_status,
        metadata={
            "source": "worker",
            "error": decision.agent_error,
            "result": validation_result,
        },
    )
    logger.warning("Decision %s failed schema validation", decision.id)
    return validation_result
