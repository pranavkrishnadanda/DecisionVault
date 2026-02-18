"""
DRF Serializers for DecisionVault.
"""

from rest_framework import serializers
from decisions.models import Decision, DecisionStatus


class DecisionSerializer(serializers.ModelSerializer):
    """Serializer for Decision model."""
    
    class Meta:
        model = Decision
        fields = [
            "id",
            "title",
            "description",
            "status",
            "priority",
            "created_by",
            "metadata",
            "workflow_started_at",
            "workflow_completed_at",
            "agent_result",
            "agent_error",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "created_by",
            "workflow_started_at",
            "workflow_completed_at",
            "agent_result",
            "agent_error",
            "created_at",
            "updated_at",
        ]
    
    def validate_priority(self, value):
        """Validate priority is within allowed range."""
        if value < -10 or value > 10:
            raise serializers.ValidationError(
                "Priority must be between -10 and 10"
            )
        return value


class DecisionSubmitSerializer(serializers.Serializer):
    """Serializer for decision submission (empty payload)."""
    
    pass


class DecisionStateTransitionSerializer(serializers.ModelSerializer):
    """Serializer for decision state transitions."""
    
    class Meta:
        model = Decision
        fields = ["status"]
        read_only_fields = ["status"]
