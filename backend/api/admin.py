# Register your models here.
from django.contrib import admin

from api.models import (
    Integration,
    IntegrationDelivery,
    IntegrationDeliveryAttempt,
    IntegrationTrigger,
    Organization,
    OrganizationMembership,
    RefreshToken,
    WebhookDelivery,
    WebhookDeliveryAttempt,
    WebhookSubscription,
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "id", "created_at", "updated_at")
    search_fields = ("name", "id")
    ordering = ("name",)


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "role", "created_at", "updated_at")
    list_filter = ("role", "organization")
    search_fields = ("user__username", "user__email", "organization__name")
    autocomplete_fields = ("user", "organization")


@admin.register(WebhookSubscription)
class WebhookSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "organization",
        "target_url",
        "is_active",
        "created_by",
        "updated_at",
    )
    list_filter = ("organization", "is_active")
    search_fields = ("id", "target_url", "created_by__username", "created_by__email")
    autocomplete_fields = ("organization", "created_by")


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "organization",
        "event_type",
        "status",
        "attempt_count",
        "max_attempts",
        "last_response_status",
        "updated_at",
    )
    list_filter = ("organization", "status", "event_type")
    search_fields = ("id", "event_type", "subscription__target_url")
    autocomplete_fields = ("organization", "subscription")


@admin.register(WebhookDeliveryAttempt)
class WebhookDeliveryAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "organization",
        "delivery",
        "attempt_number",
        "status",
        "response_status",
        "created_at",
    )
    list_filter = ("organization", "status")
    search_fields = ("id", "delivery__id", "response_request_id")
    autocomplete_fields = ("organization", "delivery")


@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "organization",
        "name",
        "connector_type",
        "is_active",
        "token_expires_at",
        "updated_at",
    )
    list_filter = ("organization", "connector_type", "is_active")
    search_fields = ("id", "name", "created_by__username", "created_by__email")
    autocomplete_fields = ("organization", "created_by")


@admin.register(IntegrationTrigger)
class IntegrationTriggerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "organization",
        "integration",
        "event_type",
        "is_active",
        "updated_at",
    )
    list_filter = ("organization", "event_type", "is_active")
    search_fields = ("id", "integration__name", "event_type")
    autocomplete_fields = ("organization", "integration")


@admin.register(IntegrationDelivery)
class IntegrationDeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "organization",
        "integration",
        "event_type",
        "status",
        "attempt_count",
        "max_attempts",
        "updated_at",
    )
    list_filter = ("organization", "status", "event_type")
    search_fields = ("id", "integration__name", "event_type")
    autocomplete_fields = ("organization", "integration", "trigger")


@admin.register(IntegrationDeliveryAttempt)
class IntegrationDeliveryAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "organization",
        "delivery",
        "attempt_number",
        "status",
        "response_status",
        "created_at",
    )
    list_filter = ("organization", "status")
    search_fields = ("id", "delivery__id", "error_message")
    autocomplete_fields = ("organization", "delivery")


@admin.register(RefreshToken)
class RefreshTokenAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "organization",
        "expires_at",
        "revoked",
        "created_at",
    )
    list_filter = ("organization", "revoked")
    search_fields = ("id", "user__username", "user__email")
    autocomplete_fields = ("user", "organization")
