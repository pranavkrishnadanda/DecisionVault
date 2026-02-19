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
