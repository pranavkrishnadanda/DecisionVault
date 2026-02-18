"""
DecisionVault services.

Business logic for:
- Audit logging
- RabbitMQ publishing
- Decision state transitions
"""

import json
import logging
import os
from typing import Optional

import pika
from django.db import transaction
from django.utils import timezone

from core.constants import DECISION_TASKS_QUEUE
from decisions.models import AuditAction, AuditLog, Decision, DecisionStatus

logger = logging.getLogger(__name__)


class AuditLogService:
    """Service for creating audit log entries."""

    @staticmethod
    def log_create(
        decision: Decision, actor_type: str = "api", actor_id: Optional[str] = None
    ):
        """
        Log decision creation.

        Args:
            decision: The decision that was created
            actor_type: Type of actor (e.g., "api", "user", "system")
            actor_id: Identifier of the actor
        """
        AuditLog.objects.create(
            entity_type="decision",
            entity_id=decision.id,
            action=AuditAction.CREATE,
            actor_type=actor_type,
            actor_id=actor_id or "",
            previous_state=None,
            current_state={
                "status": decision.status,
                "title": decision.title,
                "priority": decision.priority,
            },
            metadata={"source": "api"},
        )

    @staticmethod
    def log_submit(
        decision: Decision,
        previous_status: str,
        actor_type: str = "api",
        actor_id: Optional[str] = None,
    ):
        """
        Log decision submission.

        Args:
            decision: The decision that was submitted
            previous_status: Status before submission
            actor_type: Type of actor
            actor_id: Identifier of the actor
        """
        AuditLog.objects.create(
            entity_type="decision",
            entity_id=decision.id,
            action=AuditAction.SUBMIT,
            actor_type=actor_type,
            actor_id=actor_id or "",
            previous_state={"status": previous_status},
            current_state={
                "status": decision.status,
                "workflow_started_at": str(decision.workflow_started_at)
                if decision.workflow_started_at
                else None,
            },
            metadata={"source": "api"},
        )

    @staticmethod
    def log_retry(
        decision: Decision,
        previous_status: str,
        actor_type: str = "api",
        actor_id: Optional[str] = None,
    ):
        """Log decision retry operation."""
        AuditLog.objects.create(
            entity_type="decision",
            entity_id=decision.id,
            action=AuditAction.UPDATE,
            actor_type=actor_type,
            actor_id=actor_id or "",
            previous_state={"status": previous_status},
            current_state={
                "status": decision.status,
                "workflow_started_at": str(decision.workflow_started_at)
                if decision.workflow_started_at
                else None,
            },
            metadata={"source": "api", "operation": "retry"},
        )


class RabbitMQService:
    """Service for publishing messages to RabbitMQ."""

    QUEUE_NAME = DECISION_TASKS_QUEUE

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        """
        Initialize RabbitMQ connection.

        Args:
            host: RabbitMQ host (defaults to RABBITMQ_HOST env var)
            port: RabbitMQ port (defaults to RABBITMQ_PORT env var)
        """
        self.host = host or os.getenv("RABBITMQ_HOST", "localhost")
        self.port = port or int(os.getenv("RABBITMQ_PORT", "5672"))
        self._connection = None
        self._channel = None

    @property
    def connection(self):
        """Lazy connection initialization."""
        if self._connection is None or self._connection.is_closed:
            try:
                self._connection = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        host=self.host,
                        port=self.port,
                    )
                )
            except pika.exceptions.AMQPConnectionError:
                logger.exception(
                    "RabbitMQ connection failed for host=%s port=%s",
                    self.host,
                    self.port,
                )
                return None
        return self._connection

    @property
    def channel(self):
        """Lazy channel initialization."""
        if self._channel is None or self._channel.is_closed:
            if self.connection:
                self._channel = self.connection.channel()
                self._channel.queue_declare(
                    queue=self.QUEUE_NAME,
                    durable=True,
                )
        return self._channel

    def publish(self, decision_id: str) -> bool:
        """
        Publish decision processing message to queue.

        Args:
            decision_id: UUID of the decision to process

        Returns:
            True if message was published, False if RabbitMQ unavailable
        """
        if not self.channel:
            return False

        message = {
            "message_id": str(timezone.now().timestamp()),
            "correlation_id": f"decision_{decision_id}",
            "timestamp": timezone.now().isoformat(),
            "type": "decision.process",
            "payload": {
                "decision_id": str(decision_id),
            },
            "routing": {"expiration": 3600},
        }

        self.channel.basic_publish(
            exchange="",
            routing_key=self.QUEUE_NAME,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Persistent
            ),
        )
        return True

    def close(self):
        """Close RabbitMQ connection."""
        if self._channel and not self._channel.is_closed:
            self._channel.close()
        if self._connection and not self._connection.is_closed:
            self._connection.close()


# Singleton instance for reuse
_rabbitmq_service: Optional[RabbitMQService] = None


def get_rabbitmq_service() -> RabbitMQService:
    """Get or create RabbitMQ service singleton."""
    global _rabbitmq_service
    if _rabbitmq_service is None:
        _rabbitmq_service = RabbitMQService()
    return _rabbitmq_service


def publish_decision(decision_id: str) -> bool:
    """
    Publish decision to processing queue.

    Args:
        decision_id: UUID of the decision

    Returns:
        True if published successfully
    """
    service = get_rabbitmq_service()
    return service.publish(decision_id)


class DecisionWorkflowService:
    """Service for decision workflow operations."""

    @staticmethod
    @transaction.atomic
    def submit_decision(decision: Decision) -> bool:
        """
        Submit a decision for processing.

        Args:
            decision: The decision to submit

        Returns:
            True if submitted successfully

        Raises:
            ValueError: If decision is not in DRAFT status
        """
        if decision.status != DecisionStatus.DRAFT:
            raise ValueError(
                f"Cannot submit decision with status '{decision.status}'. "
                f"Only 'draft' decisions can be submitted."
            )

        # Store previous state for audit
        previous_status = decision.status

        # Update decision state
        decision.status = DecisionStatus.PENDING
        decision.workflow_started_at = timezone.now()
        decision.save()

        # Create audit log
        AuditLogService.log_submit(
            decision=decision, previous_status=previous_status, actor_type="api"
        )

        # Publish to queue
        published = publish_decision(str(decision.id))

        return published

    @staticmethod
    @transaction.atomic
    def retry_decision(decision: Decision) -> bool:
        """
        Retry a failed decision by re-queueing it.

        Raises:
            ValueError: If decision is not in FAILED status
        """
        if decision.status != DecisionStatus.FAILED:
            raise ValueError(
                f"Cannot retry decision with status '{decision.status}'. "
                f"Only 'failed' decisions can be retried."
            )

        previous_status = decision.status
        decision.status = DecisionStatus.PENDING
        decision.workflow_started_at = timezone.now()
        decision.workflow_completed_at = None
        decision.agent_result = {}
        decision.agent_error = ""
        decision.save(
            update_fields=[
                "status",
                "workflow_started_at",
                "workflow_completed_at",
                "agent_result",
                "agent_error",
                "updated_at",
            ]
        )

        AuditLogService.log_retry(
            decision=decision,
            previous_status=previous_status,
            actor_type="api",
        )

        published = publish_decision(str(decision.id))
        return published
