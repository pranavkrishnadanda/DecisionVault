import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Organization(models.Model):
    """Tenant boundary for all operator data."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organizations"
        ordering = ["name"]

    def __str__(self):
        return self.name


class OrganizationRole(models.TextChoices):
    ADMIN = "admin", "Admin"
    OPERATOR = "operator", "Operator"
    VIEWER = "viewer", "Viewer"


class OrganizationMembership(models.Model):
    """User role assignment inside an organization."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
    )
    organization = models.ForeignKey(
        "api.Organization",
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(
        max_length=24,
        choices=OrganizationRole.choices,
        default=OrganizationRole.OPERATOR,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organization_memberships"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organization"],
                name="unique_user_organization_membership",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "role"]),
            models.Index(fields=["user", "organization"]),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.organization_id}:{self.role}"


WEBHOOK_EVENT_DECISION_CREATED = "decision.created"
WEBHOOK_EVENT_DECISION_UPDATED = "decision.updated"
WEBHOOK_EVENT_DECISION_SUBMITTED = "decision.submitted"
WEBHOOK_EVENT_DECISION_RETRY_REQUESTED = "decision.retry_requested"
WEBHOOK_EVENT_DECISION_FAILED = "decision.failed"
WEBHOOK_EVENT_DECISION_COMPLETED = "decision.completed"

WEBHOOK_EVENT_TYPES = (
    WEBHOOK_EVENT_DECISION_CREATED,
    WEBHOOK_EVENT_DECISION_UPDATED,
    WEBHOOK_EVENT_DECISION_SUBMITTED,
    WEBHOOK_EVENT_DECISION_RETRY_REQUESTED,
    WEBHOOK_EVENT_DECISION_FAILED,
    WEBHOOK_EVENT_DECISION_COMPLETED,
)

INTEGRATION_EVENT_DECISION_FAILED = "decision.failed"
INTEGRATION_EVENT_DECISION_COMPLETED = "decision.completed"
INTEGRATION_EVENT_WEBHOOK_FAILED = "webhook.failed"

INTEGRATION_EVENT_TYPES = (
    INTEGRATION_EVENT_DECISION_FAILED,
    INTEGRATION_EVENT_DECISION_COMPLETED,
    INTEGRATION_EVENT_WEBHOOK_FAILED,
)


class WebhookSubscription(models.Model):
    """Organization-scoped endpoint registration for outbound events."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "api.Organization",
        on_delete=models.CASCADE,
        related_name="webhook_subscriptions",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="webhook_subscriptions",
    )
    target_url = models.URLField(max_length=500)
    signing_secret = models.CharField(max_length=255)
    events = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "webhook_subscriptions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
            models.Index(fields=["organization", "created_at"]),
        ]

    def __str__(self):
        return f"{self.organization_id}:{self.target_url}"


class WebhookDelivery(models.Model):
    """Persistent webhook delivery job for retryable async processing."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "api.Organization",
        on_delete=models.CASCADE,
        related_name="webhook_deliveries",
    )
    subscription = models.ForeignKey(
        "api.WebhookSubscription",
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    event_type = models.CharField(max_length=120)
    payload = models.JSONField(default=dict)
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.PENDING,
    )
    attempt_count = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    last_response_status = models.PositiveIntegerField(null=True, blank=True)
    last_error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "webhook_deliveries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["subscription", "status"]),
            models.Index(fields=["next_retry_at"]),
        ]

    def __str__(self):
        return f"{self.organization_id}:{self.subscription_id}:{self.event_type}"


class WebhookDeliveryAttempt(models.Model):
    """Append-only delivery attempt log for observability and retries."""

    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "api.Organization",
        on_delete=models.CASCADE,
        related_name="webhook_delivery_attempts",
    )
    delivery = models.ForeignKey(
        "api.WebhookDelivery",
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    attempt_number = models.PositiveIntegerField()
    status = models.CharField(max_length=24, choices=Status.choices)
    response_status = models.PositiveIntegerField(null=True, blank=True)
    response_request_id = models.CharField(max_length=255, blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "webhook_delivery_attempts"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["organization", "delivery"]),
            models.Index(fields=["delivery", "attempt_number"]),
            models.Index(fields=["created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["delivery", "attempt_number"],
                name="unique_webhook_delivery_attempt_number",
            )
        ]

    def __str__(self):
        return f"{self.delivery_id}:{self.attempt_number}:{self.status}"


class Integration(models.Model):
    """Organization-scoped external connector configuration."""

    class ConnectorType(models.TextChoices):
        SLACK = "slack", "Slack"
        TEAMS = "teams", "Teams"
        EMAIL = "email", "Email"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "api.Organization",
        on_delete=models.CASCADE,
        related_name="integrations",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="integrations",
    )
    name = models.CharField(max_length=120)
    connector_type = models.CharField(max_length=24, choices=ConnectorType.choices)
    config = models.JSONField(default=dict)
    credentials_encrypted = models.TextField(default="")
    token_expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "integrations"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="unique_integration_name_per_org",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "connector_type"]),
            models.Index(fields=["organization", "is_active"]),
            models.Index(fields=["organization", "created_at"]),
        ]

    def __str__(self):
        return f"{self.organization_id}:{self.connector_type}:{self.name}"


class IntegrationTrigger(models.Model):
    """Organization-scoped event trigger bound to a connector."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "api.Organization",
        on_delete=models.CASCADE,
        related_name="integration_triggers",
    )
    integration = models.ForeignKey(
        "api.Integration",
        on_delete=models.CASCADE,
        related_name="triggers",
    )
    event_type = models.CharField(max_length=120)
    message_template = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "integration_triggers"
        ordering = ["event_type", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["integration", "event_type"],
                name="unique_integration_trigger_event",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "event_type", "is_active"]),
            models.Index(fields=["integration", "is_active"]),
        ]

    def __str__(self):
        return f"{self.integration_id}:{self.event_type}:{self.is_active}"


class IntegrationDelivery(models.Model):
    """Persistent integration delivery job for async processing and retries."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "api.Organization",
        on_delete=models.CASCADE,
        related_name="integration_deliveries",
    )
    integration = models.ForeignKey(
        "api.Integration",
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    trigger = models.ForeignKey(
        "api.IntegrationTrigger",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deliveries",
    )
    event_type = models.CharField(max_length=120)
    payload = models.JSONField(default=dict)
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.PENDING,
    )
    attempt_count = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    last_response_status = models.PositiveIntegerField(null=True, blank=True)
    last_error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "integration_deliveries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["integration", "status"]),
            models.Index(fields=["next_retry_at"]),
        ]

    def __str__(self):
        return f"{self.organization_id}:{self.integration_id}:{self.event_type}"


class IntegrationDeliveryAttempt(models.Model):
    """Append-only log of integration delivery attempts."""

    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "api.Organization",
        on_delete=models.CASCADE,
        related_name="integration_delivery_attempts",
    )
    delivery = models.ForeignKey(
        "api.IntegrationDelivery",
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    attempt_number = models.PositiveIntegerField()
    status = models.CharField(max_length=24, choices=Status.choices)
    response_status = models.PositiveIntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "integration_delivery_attempts"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["organization", "delivery"]),
            models.Index(fields=["delivery", "attempt_number"]),
            models.Index(fields=["created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["delivery", "attempt_number"],
                name="unique_integration_delivery_attempt_number",
            )
        ]

    def __str__(self):
        return f"{self.delivery_id}:{self.attempt_number}:{self.status}"


def get_default_organization() -> Organization:
    """Return singleton default organization, creating it when missing."""
    organization, _created = Organization.objects.get_or_create(name="Default")
    return organization


def get_default_organization_id() -> uuid.UUID:
    """Return UUID used as FK default for org-scoped models."""
    return get_default_organization().id


@receiver(post_save, sender=get_user_model())
def ensure_default_organization_membership(sender, instance, created, **kwargs):
    """Backwards-compatible membership bootstrap for newly created users."""
    if not created:
        return

    organization = get_default_organization()
    is_first_member = not OrganizationMembership.objects.filter(
        organization=organization
    ).exists()
    role = (
        OrganizationRole.ADMIN
        if instance.is_staff or instance.is_superuser or is_first_member
        else OrganizationRole.OPERATOR
    )
    OrganizationMembership.objects.get_or_create(
        user=instance,
        organization=organization,
        defaults={"role": role},
    )
