from django.contrib import admin

from decisions.models import (
    AuditLog,
    Decision,
    SavedView,
    TablePreference,
    Workflow,
    WorkflowStep,
)


@admin.register(Decision)
class DecisionAdmin(admin.ModelAdmin):
    list_display = ("id", "organization", "title", "status", "created_by", "updated_at")
    list_filter = ("organization", "status")
    search_fields = ("id", "title", "description", "created_by")
    autocomplete_fields = ("organization",)


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ("id", "organization", "decision", "status", "updated_at")
    list_filter = ("organization", "status")
    search_fields = ("id", "name", "description", "decision__id")
    autocomplete_fields = ("organization", "decision")


@admin.register(WorkflowStep)
class WorkflowStepAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "organization",
        "workflow",
        "step_number",
        "agent_type",
        "status",
    )
    list_filter = ("organization", "status", "agent_type")
    search_fields = ("id", "workflow__id", "action", "agent_type")
    autocomplete_fields = ("organization", "workflow")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "organization",
        "entity_type",
        "entity_id",
        "action",
        "actor_type",
        "timestamp",
    )
    list_filter = ("organization", "entity_type", "action", "actor_type")
    search_fields = ("id", "entity_id", "actor_id")
    autocomplete_fields = ("organization",)


@admin.register(SavedView)
class SavedViewAdmin(admin.ModelAdmin):
    list_display = ("id", "organization", "user", "name", "updated_at")
    list_filter = ("organization",)
    search_fields = ("id", "name", "user__username", "user__email")
    autocomplete_fields = ("organization", "user")


@admin.register(TablePreference)
class TablePreferenceAdmin(admin.ModelAdmin):
    list_display = ("id", "organization", "user", "table", "density", "updated_at")
    list_filter = ("organization", "table", "density")
    search_fields = ("id", "table", "user__username", "user__email")
    autocomplete_fields = ("organization", "user")
