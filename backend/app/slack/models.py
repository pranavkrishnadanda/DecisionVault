import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class SlackIntegration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(
        "api.Organization",
        on_delete=models.CASCADE,
        related_name="slack_integrations",
    )
    team_id = models.CharField(max_length=64)
    team_name = models.CharField(max_length=255)
    encrypted_token = models.TextField()
    bot_user_id = models.CharField(max_length=64, blank=True, default="")
    installed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="installed_slack_integrations",
    )
    installed_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "slack_integrations"
        indexes = [
            models.Index(fields=["org", "team_id"]),
            models.Index(fields=["org", "is_active"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["org", "team_id"],
                name="unique_slack_team_per_org",
            )
        ]


class SlackAuditLog(models.Model):
    class Action(models.TextChoices):
        INSTALL_INIT = "install_init", "Install Init"
        INSTALL = "install", "Install"
        CHANNEL_LIST = "channel_list", "Channel List"
        MESSAGE_FETCH = "message_fetch", "Message Fetch"
        TEST_SEND = "test_send", "Test Send"
        EVENT_RECEIVED = "event_received", "Event Received"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    integration = models.ForeignKey(
        "slack_integration.SlackIntegration",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=64, choices=Action.choices)
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="slack_audit_logs",
    )
    details = models.JSONField(default=dict)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "slack_audit_logs"
        indexes = [
            models.Index(fields=["action", "timestamp"]),
            models.Index(fields=["integration", "timestamp"]),
        ]


class SlackUserCache(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    integration = models.ForeignKey(
        "slack_integration.SlackIntegration",
        on_delete=models.CASCADE,
        related_name="user_cache_entries",
    )
    slack_user_id = models.CharField(max_length=64)
    display_name = models.CharField(max_length=255, blank=True, default="")
    real_name = models.CharField(max_length=255, blank=True, default="")
    avatar_url = models.URLField(max_length=500, blank=True, default="")
    cached_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "slack_user_cache"
        constraints = [
            models.UniqueConstraint(
                fields=["integration", "slack_user_id"],
                name="unique_slack_user_cache_per_integration",
            )
        ]
        indexes = [models.Index(fields=["integration", "cached_at"])]


class SlackIntegrationTestLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    integration = models.ForeignKey(
        "slack_integration.SlackIntegration",
        on_delete=models.CASCADE,
        related_name="test_logs",
    )
    channel_id = models.CharField(max_length=64)
    success = models.BooleanField(default=False)
    error = models.TextField(blank=True, default="")
    message_ts = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "slack_integration_test_logs"
        indexes = [models.Index(fields=["integration", "created_at"])]
