"""
DecisionVault Core Models.

Implements the core domain model for decision workflow management:
- Decision: Core decision entity with embedded workflow state
- Workflow: Workflow definition and execution tracking
- WorkflowStep: Individual workflow steps
- AuditLog: Append-only audit trail
"""

import uuid

from django.db import models
from django.utils import timezone

from api.models import get_default_organization_id


class DecisionStatus(models.TextChoices):
    """Decision lifecycle status choices."""

    DRAFT = "draft", "Draft"
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class DecisionManager(models.Manager):
    """Custom manager for Decision model with filtered querysets."""

    def draft(self):
        """Return all draft decisions."""
        return self.filter(status=DecisionStatus.DRAFT)

    def pending(self):
        """Return all pending decisions."""
        return self.filter(status=DecisionStatus.PENDING)

    def processing(self):
        """Return all processing decisions."""
        return self.filter(status=DecisionStatus.PROCESSING)

    def completed(self):
        """Return all completed decisions."""
        return self.filter(status=DecisionStatus.COMPLETED)

    def failed(self):
        """Return all failed decisions."""
        return self.filter(status=DecisionStatus.FAILED)


class Decision(models.Model):
    """
    Core decision entity for DecisionVault.

    Represents a decision that needs to be processed through a workflow.
    The workflow state is embedded in this model for MVP v1 simplicity.

    Status transitions:
        DRAFT -> PENDING -> PROCESSING -> COMPLETED | FAILED
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the decision",
    )
    organization = models.ForeignKey(
        "api.Organization",
        on_delete=models.CASCADE,
        related_name="decisions",
        default=get_default_organization_id,
        db_index=True,
    )
    title = models.CharField(
        max_length=255, help_text="Human-readable title for the decision"
    )
    description = models.TextField(help_text="Detailed description of the decision")
    status = models.CharField(
        max_length=20,
        choices=DecisionStatus.choices,
        default=DecisionStatus.DRAFT,
        db_index=True,
        help_text="Current status of the decision",
    )
    priority = models.IntegerField(
        default=0, help_text="Priority level from -10 (lowest) to 10 (highest)"
    )
    created_by = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Identifier of the user who created this decision",
    )
    metadata = models.JSONField(
        default=dict, blank=True, help_text="Additional metadata as JSON"
    )

    # Embedded workflow state (MVP v1 - simplified)
    workflow_started_at = models.DateTimeField(
        null=True, blank=True, help_text="When workflow processing started"
    )
    workflow_completed_at = models.DateTimeField(
        null=True, blank=True, help_text="When workflow processing completed"
    )
    agent_result = models.JSONField(
        default=dict, blank=True, help_text="Result from agent execution"
    )
    agent_error = models.TextField(
        blank=True, default="", help_text="Error message from agent execution"
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, help_text="When the decision was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="When the decision was last updated"
    )

    objects = DecisionManager()

    class Meta:
        db_table = "decisions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization"]),
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "updated_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["updated_at"]),
            models.Index(fields=["created_by", "status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]
        verbose_name = "Decision"
        verbose_name_plural = "Decisions"
        managed = True

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """Validate priority range before saving."""
        if self.priority < -10 or self.priority > 10:
            raise ValueError("Priority must be between -10 and 10")
        super().save(*args, **kwargs)


class WorkflowStatus(models.TextChoices):
    """Workflow execution status choices."""

    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class Workflow(models.Model):
    """
    Workflow definition and execution tracking.

    Defines a workflow that can be executed for a decision.
    Contains steps that are executed in sequence.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the workflow",
    )
    organization = models.ForeignKey(
        "api.Organization",
        on_delete=models.CASCADE,
        related_name="workflows",
        default=get_default_organization_id,
        db_index=True,
    )
    decision = models.ForeignKey(
        Decision,
        on_delete=models.CASCADE,
        related_name="workflows",
        help_text="The decision this workflow is for",
    )
    status = models.CharField(
        max_length=20,
        choices=WorkflowStatus.choices,
        default=WorkflowStatus.PENDING,
        db_index=True,
        help_text="Current status of the workflow",
    )
    name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Optional name for the workflow",
    )
    description = models.TextField(
        blank=True, default="", help_text="Optional description of the workflow"
    )
    timeout_sec = models.IntegerField(
        default=300, help_text="Timeout in seconds for workflow execution"
    )
    max_retries = models.IntegerField(
        default=3, help_text="Maximum number of retries for failed steps"
    )

    # Execution tracking
    started_at = models.DateTimeField(
        null=True, blank=True, help_text="When the workflow started executing"
    )
    completed_at = models.DateTimeField(
        null=True, blank=True, help_text="When the workflow completed"
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="When the workflow was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="When the workflow was last updated"
    )

    class Meta:
        db_table = "workflows"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization"]),
            models.Index(fields=["decision", "status"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]
        verbose_name = "Workflow"
        verbose_name_plural = "Workflows"
        managed = True

    def __str__(self):
        return self.name or str(self.decision)


class StepStatus(models.TextChoices):
    """Workflow step execution status choices."""

    PENDING = "pending", "Pending"
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    RETRYING = "retrying", "Retrying"
    SKIPPED = "skipped", "Skipped"


class WorkflowStep(models.Model):
    """
    Individual workflow step.

    Represents a single step in a workflow that executes a specific action
    using a specific agent type.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the step",
    )
    organization = models.ForeignKey(
        "api.Organization",
        on_delete=models.CASCADE,
        related_name="workflow_steps",
        default=get_default_organization_id,
        db_index=True,
    )
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name="steps",
        help_text="The workflow this step belongs to",
    )
    step_number = models.IntegerField(
        help_text="Order of this step in the workflow (1-indexed)"
    )
    agent_type = models.CharField(
        max_length=50, help_text="Type of agent to execute this step"
    )
    action = models.CharField(
        max_length=100, help_text="Action to be performed by the agent"
    )
    status = models.CharField(
        max_length=20,
        choices=StepStatus.choices,
        default=StepStatus.PENDING,
        db_index=True,
        help_text="Current status of the step",
    )
    result = models.JSONField(
        default=dict, blank=True, help_text="Result from step execution"
    )
    error = models.JSONField(
        default=dict, blank=True, help_text="Error details if step failed"
    )
    retry_count = models.IntegerField(
        default=0, help_text="Number of times this step has been retried"
    )
    max_retries = models.IntegerField(
        default=3, help_text="Maximum number of retries allowed"
    )
    timeout_sec = models.IntegerField(
        default=300, help_text="Timeout in seconds for this step"
    )

    # Execution tracking
    started_at = models.DateTimeField(
        null=True, blank=True, help_text="When the step started executing"
    )
    completed_at = models.DateTimeField(
        null=True, blank=True, help_text="When the step completed"
    )

    class Meta:
        db_table = "workflow_steps"
        ordering = ["workflow", "step_number"]
        unique_together = ["workflow", "step_number"]
        indexes = [
            models.Index(fields=["organization"]),
            models.Index(fields=["workflow", "status"]),
            models.Index(fields=["status"]),
            models.Index(fields=["agent_type", "status"]),
        ]
        verbose_name = "Workflow Step"
        verbose_name_plural = "Workflow Steps"
        managed = True

    def __str__(self):
        return f"Step {self.step_number}: {self.action}"


class AuditAction(models.TextChoices):
    """Audit log action choices."""

    CREATE = "create", "Create"
    UPDATE = "update", "Update"
    SUBMIT = "submit", "Submit"
    PROCESSING_START = "processing_start", "Processing Start"
    PROCESSING_COMPLETE = "processing_complete", "Processing Complete"
    PROCESSING_FAILED = "processing_failed", "Processing Failed"


class AuditLogManager(models.Manager):
    """Custom manager for AuditLog model with filtered querysets."""

    def for_entity(self, entity_type: str, entity_id: uuid.UUID):
        """Return all audit logs for a specific entity."""
        return self.filter(entity_type=entity_type, entity_id=entity_id).order_by(
            "timestamp"
        )

    def by_action(self, action: str):
        """Return all audit logs with a specific action."""
        return self.filter(action=action)

    def by_actor(self, actor_type: str):
        """Return all audit logs by a specific actor type."""
        return self.filter(actor_type=actor_type)


class AuditLog(models.Model):
    """
    Append-only audit trail.

    Records all significant actions in the system for compliance
    and debugging purposes. MVP v1 uses simple append-only logging
    without cryptographic chaining (deferred to v2).

    Critical fields (entity_type, entity_id, action, timestamp) should
    never be modified after creation.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the audit log entry",
    )
    organization = models.ForeignKey(
        "api.Organization",
        on_delete=models.CASCADE,
        related_name="audit_logs",
        default=get_default_organization_id,
        db_index=True,
    )
    entity_type = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Type of entity being audited (e.g., 'decision', 'workflow')",
    )
    entity_id = models.UUIDField(
        db_index=True, help_text="ID of the entity being audited"
    )
    action = models.CharField(
        max_length=30,
        choices=AuditAction.choices,
        db_index=True,
        help_text="Action that was performed",
    )
    actor_type = models.CharField(
        max_length=30,
        db_index=True,
        help_text="Type of actor that performed the action (e.g., 'user', 'system')",
    )
    actor_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Identifier of the actor that performed the action",
    )
    timestamp = models.DateTimeField(
        auto_now_add=True, db_index=True, help_text="When the action was performed"
    )
    previous_state = models.JSONField(
        null=True, blank=True, help_text="State before the action (for updates)"
    )
    current_state = models.JSONField(
        null=True, blank=True, help_text="State after the action"
    )
    metadata = models.JSONField(
        default=dict, blank=True, help_text="Additional metadata about the action"
    )

    objects = AuditLogManager()

    class Meta:
        db_table = "audit_logs"
        ordering = ["timestamp"]
        indexes = [
            models.Index(fields=["organization"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["timestamp"]),
            models.Index(fields=["action"]),
            models.Index(fields=["actor_type"]),
        ]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        managed = True

    def __str__(self):
        return f"AuditLog(entity_type={self.entity_type}, action={self.action}, entity_id={self.entity_id})"

    def save(self, *args, **kwargs):
        """
        Prevent modification of critical fields after creation.

        In MVP v1, this is a soft enforcement. Full immutability
        with database triggers will be added in v2.
        """
        if self.pk:  # Updating existing record
            try:
                old = AuditLog.objects.get(pk=self.pk)
                # Prevent changes to critical fields
                if old.entity_type != self.entity_type:
                    raise ValueError("Cannot modify entity_type after creation")
                if old.entity_id != self.entity_id:
                    raise ValueError("Cannot modify entity_id after creation")
                if old.action != self.action:
                    raise ValueError("Cannot modify action after creation")
                if old.timestamp != self.timestamp:
                    raise ValueError("Cannot modify timestamp after creation")
            except AuditLog.DoesNotExist:
                pass  # Should not happen, but allow save
        super().save(*args, **kwargs)


class SavedView(models.Model):
    """User-owned saved filter presets for operator decisions list."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the saved view",
    )
    organization = models.ForeignKey(
        "api.Organization",
        on_delete=models.CASCADE,
        related_name="saved_views",
        default=get_default_organization_id,
        db_index=True,
    )
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="saved_views",
        help_text="Owner of the saved view",
    )
    name = models.CharField(max_length=120, help_text="Saved view display name")
    filters = models.JSONField(default=dict, help_text="Serialized decision filters")
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="When saved view was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="When saved view was last updated"
    )

    class Meta:
        db_table = "saved_views"
        ordering = ["name", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user", "name"],
                name="unique_org_user_saved_view_name",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "user"]),
            models.Index(fields=["user", "created_at"]),
        ]
        verbose_name = "Saved View"
        verbose_name_plural = "Saved Views"
        managed = True

    def __str__(self):
        return f"{self.user.username}:{self.name}"


def default_decisions_columns() -> list[str]:
    return ["id", "workflow", "status", "updated"]


def default_decisions_column_order() -> list[str]:
    return ["id", "workflow", "status", "updated"]


class TableDensity(models.TextChoices):
    COMPACT = "compact", "Compact"
    COMFORTABLE = "comfortable", "Comfortable"
    SPACIOUS = "spacious", "Spacious"


class TablePreference(models.Model):
    """User-owned table presentation preferences."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for table preference",
    )
    organization = models.ForeignKey(
        "api.Organization",
        on_delete=models.CASCADE,
        related_name="table_preferences",
        default=get_default_organization_id,
        db_index=True,
    )
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="table_preferences",
        help_text="Owner of table preferences",
    )
    table = models.CharField(
        max_length=64,
        help_text="Table identifier this preference belongs to",
    )
    visible_columns = models.JSONField(
        default=default_decisions_columns,
        help_text="Visible columns in render order",
    )
    column_order = models.JSONField(
        default=default_decisions_column_order,
        help_text="Full column order used by customization UI",
    )
    density = models.CharField(
        max_length=24,
        choices=TableDensity.choices,
        default=TableDensity.COMFORTABLE,
        help_text="Density mode for row height",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "table_preferences"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user", "table"],
                name="unique_org_user_table_preference",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "user", "table"]),
            models.Index(fields=["user", "table"]),
        ]
        ordering = ["table"]
        verbose_name = "Table Preference"
        verbose_name_plural = "Table Preferences"
        managed = True

    def __str__(self):
        return f"{self.user.username}:{self.table}"
