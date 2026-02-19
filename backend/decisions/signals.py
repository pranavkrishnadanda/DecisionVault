"""Decision lifecycle signal hooks."""

from __future__ import annotations

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from api.models import (
    INTEGRATION_EVENT_DECISION_COMPLETED,
    INTEGRATION_EVENT_DECISION_FAILED,
)
from api.services.integration_dispatcher import dispatch_event_to_integrations
from decisions.models import Decision, DecisionStatus


@receiver(pre_save, sender=Decision)
def cache_previous_decision_status(sender, instance: Decision, **kwargs):
    if instance.pk is None:
        instance._previous_status = None
        return

    previous = (
        Decision.objects.filter(pk=instance.pk).values_list("status", flat=True).first()
    )
    instance._previous_status = previous


@receiver(post_save, sender=Decision)
def emit_integration_events_for_decision_status(
    sender, instance: Decision, created: bool, **kwargs
):
    if created:
        return

    previous_status = getattr(instance, "_previous_status", None)
    if previous_status == instance.status:
        return

    if instance.status == DecisionStatus.FAILED:
        event_type = INTEGRATION_EVENT_DECISION_FAILED
    elif instance.status == DecisionStatus.COMPLETED:
        event_type = INTEGRATION_EVENT_DECISION_COMPLETED
    else:
        return

    dispatch_event_to_integrations(
        organization=instance.organization,
        event_type=event_type,
        payload={
            "decision_id": str(instance.id),
            "status": instance.status,
            "previous_status": previous_status,
        },
    )
