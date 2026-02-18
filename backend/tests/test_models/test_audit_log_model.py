"""
Tests for AuditLog model.

Follows TDD: Tests are written before implementation.
"""

import pytest
import uuid
from django.core.exceptions import ValidationError
from django.utils import timezone

from decisions.models import AuditLog, AuditAction


@pytest.mark.django_db
class TestAuditLogModel:
    """Test AuditLog model structure and behavior."""

    def test_create_audit_log_with_required_fields(self, audit_log_data):
        """
        Should create an audit log with required fields.
        
        Required fields: entity_type, entity_id, action, actor_type
        """
        audit_log = AuditLog.objects.create(
            entity_type=audit_log_data["entity_type"],
            entity_id=uuid.uuid4(),
            action=audit_log_data["action"],
            actor_type=audit_log_data["actor_type"]
        )
        
        assert audit_log.id is not None
        assert isinstance(audit_log.id, uuid.UUID)
        assert audit_log.entity_type == audit_log_data["entity_type"]
        assert isinstance(audit_log.entity_id, uuid.UUID)
        assert audit_log.action == audit_log_data["action"]
        assert audit_log.actor_type == audit_log_data["actor_type"]

    def test_audit_log_actor_id_is_optional(self, audit_log_data):
        """
        Should allow actor_id to be blank.
        """
        audit_log = AuditLog.objects.create(
            entity_type=audit_log_data["entity_type"],
            entity_id=uuid.uuid4(),
            action=audit_log_data["action"],
            actor_type=audit_log_data["actor_type"],
            actor_id=""
        )
        
        assert audit_log.actor_id == ""

    def test_audit_log_timestamp_is_auto_set(self, audit_log_data):
        """
        Should automatically set timestamp on save.
        """
        before = timezone.now()
        audit_log = AuditLog.objects.create(
            entity_type=audit_log_data["entity_type"],
            entity_id=uuid.uuid4(),
            action=audit_log_data["action"],
            actor_type=audit_log_data["actor_type"]
        )
        after = timezone.now()
        
        assert audit_log.timestamp is not None
        assert before <= audit_log.timestamp <= after

    def test_audit_log_previous_state_nullable(self, audit_log_data):
        """
        Should allow previous_state to be null.
        """
        audit_log = AuditLog.objects.create(
            entity_type=audit_log_data["entity_type"],
            entity_id=uuid.uuid4(),
            action=audit_log_data["action"],
            actor_type=audit_log_data["actor_type"],
            previous_state=None
        )
        
        assert audit_log.previous_state is None

    def test_audit_log_previous_state_stores_json(self, audit_log_data):
        """
        Should store arbitrary JSON in previous_state.
        """
        previous_state = {
            "status": "draft",
            "title": "Old Title",
            "nested": {"key": "value"}
        }
        
        audit_log = AuditLog.objects.create(
            entity_type=audit_log_data["entity_type"],
            entity_id=uuid.uuid4(),
            action=audit_log_data["action"],
            actor_type=audit_log_data["actor_type"],
            previous_state=previous_state
        )
        
        assert audit_log.previous_state == previous_state

    def test_audit_log_current_state_nullable(self, audit_log_data):
        """
        Should allow current_state to be null.
        """
        audit_log = AuditLog.objects.create(
            entity_type=audit_log_data["entity_type"],
            entity_id=uuid.uuid4(),
            action=audit_log_data["action"],
            actor_type=audit_log_data["actor_type"],
            current_state=None
        )
        
        assert audit_log.current_state is None

    def test_audit_log_current_state_stores_json(self, audit_log_data):
        """
        Should store arbitrary JSON in current_state.
        """
        current_state = {
            "status": "pending",
            "title": "New Title",
            "nested": {"key": "new_value"}
        }
        
        audit_log = AuditLog.objects.create(
            entity_type=audit_log_data["entity_type"],
            entity_id=uuid.uuid4(),
            action=audit_log_data["action"],
            actor_type=audit_log_data["actor_type"],
            current_state=current_state
        )
        
        assert audit_log.current_state == current_state

    def test_audit_log_metadata_default_is_empty_dict(self, audit_log_data):
        """
        Should initialize metadata as empty dict by default.
        """
        audit_log = AuditLog.objects.create(
            entity_type=audit_log_data["entity_type"],
            entity_id=uuid.uuid4(),
            action=audit_log_data["action"],
            actor_type=audit_log_data["actor_type"]
        )
        
        assert audit_log.metadata == {}

    def test_audit_log_metadata_stores_json(self, audit_log_data):
        """
        Should store arbitrary JSON in metadata.
        """
        metadata = {
            "source": "api",
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0"
        }
        
        audit_log = AuditLog.objects.create(
            entity_type=audit_log_data["entity_type"],
            entity_id=uuid.uuid4(),
            action=audit_log_data["action"],
            actor_type=audit_log_data["actor_type"],
            metadata=metadata
        )
        
        assert audit_log.metadata == metadata

    def test_audit_log_str_representation(self, audit_log_data):
        """
        Should return descriptive string representation.
        """
        entity_id = uuid.uuid4()
        audit_log = AuditLog.objects.create(
            entity_type=audit_log_data["entity_type"],
            entity_id=entity_id,
            action=audit_log_data["action"],
            actor_type=audit_log_data["actor_type"]
        )
        
        expected = f"AuditLog(entity_type=decision, action=create, entity_id={entity_id})"
        assert str(audit_log) == expected


@pytest.mark.django_db
class TestAuditActionChoices:
    """Test AuditLog action choices."""

    def test_action_choices_are_valid(self):
        """
        Should have valid action choices defined.
        """
        expected_actions = [
            "create", "update", "submit",
            "processing_start", "processing_complete", "processing_failed"
        ]
        actual_actions = [choice[0] for choice in AuditAction.choices]
        
        assert sorted(actual_actions) == sorted(expected_actions)

    def test_create_action(self, audit_log_data):
        """
        Should allow 'create' action.
        """
        audit_log = AuditLog.objects.create(
            entity_type=audit_log_data["entity_type"],
            entity_id=uuid.uuid4(),
            action=AuditAction.CREATE,
            actor_type=audit_log_data["actor_type"]
        )
        
        assert audit_log.action == AuditAction.CREATE

    def test_update_action(self, audit_log_data):
        """
        Should allow 'update' action.
        """
        audit_log = AuditLog.objects.create(
            entity_type=audit_log_data["entity_type"],
            entity_id=uuid.uuid4(),
            action=AuditAction.UPDATE,
            actor_type=audit_log_data["actor_type"]
        )
        
        assert audit_log.action == AuditAction.UPDATE

    def test_submit_action(self, audit_log_data):
        """
        Should allow 'submit' action.
        """
        audit_log = AuditLog.objects.create(
            entity_type=audit_log_data["entity_type"],
            entity_id=uuid.uuid4(),
            action=AuditAction.SUBMIT,
            actor_type=audit_log_data["actor_type"]
        )
        
        assert audit_log.action == AuditAction.SUBMIT

    def test_processing_start_action(self, audit_log_data):
        """
        Should allow 'processing_start' action.
        """
        audit_log = AuditLog.objects.create(
            entity_type=audit_log_data["entity_type"],
            entity_id=uuid.uuid4(),
            action=AuditAction.PROCESSING_START,
            actor_type=audit_log_data["actor_type"]
        )
        
        assert audit_log.action == AuditAction.PROCESSING_START

    def test_processing_complete_action(self, audit_log_data):
        """
        Should allow 'processing_complete' action.
        """
        audit_log = AuditLog.objects.create(
            entity_type=audit_log_data["entity_type"],
            entity_id=uuid.uuid4(),
            action=AuditAction.PROCESSING_COMPLETE,
            actor_type=audit_log_data["actor_type"]
        )
        
        assert audit_log.action == AuditAction.PROCESSING_COMPLETE

    def test_processing_failed_action(self, audit_log_data):
        """
        Should allow 'processing_failed' action.
        """
        audit_log = AuditLog.objects.create(
            entity_type=audit_log_data["entity_type"],
            entity_id=uuid.uuid4(),
            action=AuditAction.PROCESSING_FAILED,
            actor_type=audit_log_data["actor_type"]
        )
        
        assert audit_log.action == AuditAction.PROCESSING_FAILED


@pytest.mark.django_db
class TestAuditLogManager:
    """Test AuditLog model manager and querysets."""

    def test_manager_has_custom_methods(self):
        """
        Should have custom manager methods.
        """
        assert hasattr(AuditLog.objects, "for_entity")
        assert hasattr(AuditLog.objects, "by_action")
        assert hasattr(AuditLog.objects, "by_actor")

    def test_for_entity_filters_correctly(self, audit_log_data):
        """
        Should filter audit logs by entity_type and entity_id.
        """
        entity_id = uuid.uuid4()
        other_entity_id = uuid.uuid4()
        
        AuditLog.objects.create(
            entity_type="decision",
            entity_id=entity_id,
            action=AuditAction.CREATE,
            actor_type="user"
        )
        AuditLog.objects.create(
            entity_type="decision",
            entity_id=other_entity_id,
            action=AuditAction.CREATE,
            actor_type="user"
        )
        AuditLog.objects.create(
            entity_type="workflow",
            entity_id=entity_id,
            action=AuditAction.CREATE,
            actor_type="system"
        )
        
        logs = AuditLog.objects.for_entity("decision", entity_id)
        
        assert logs.count() == 1
        assert logs.first().entity_id == entity_id

    def test_by_action_filters_correctly(self, audit_log_data):
        """
        Should filter audit logs by action.
        """
        AuditLog.objects.create(
            entity_type="decision",
            entity_id=uuid.uuid4(),
            action=AuditAction.CREATE,
            actor_type="user"
        )
        AuditLog.objects.create(
            entity_type="decision",
            entity_id=uuid.uuid4(),
            action=AuditAction.UPDATE,
            actor_type="user"
        )
        AuditLog.objects.create(
            entity_type="decision",
            entity_id=uuid.uuid4(),
            action=AuditAction.CREATE,
            actor_type="system"
        )
        
        logs = AuditLog.objects.by_action(AuditAction.CREATE)
        
        assert logs.count() == 2

    def test_by_actor_filters_correctly(self, audit_log_data):
        """
        Should filter audit logs by actor_type.
        """
        AuditLog.objects.create(
            entity_type="decision",
            entity_id=uuid.uuid4(),
            action=AuditAction.CREATE,
            actor_type="user"
        )
        AuditLog.objects.create(
            entity_type="decision",
            entity_id=uuid.uuid4(),
            action=AuditAction.CREATE,
            actor_type="system"
        )
        AuditLog.objects.create(
            entity_type="decision",
            entity_id=uuid.uuid4(),
            action=AuditAction.UPDATE,
            actor_type="user"
        )
        
        logs = AuditLog.objects.by_actor("user")
        
        assert logs.count() == 2

    def test_for_entity_returns_audit_trail(self, audit_log_data):
        """
        Should return complete audit trail for an entity ordered by timestamp.
        """
        entity_id = uuid.uuid4()
        
        log1 = AuditLog.objects.create(
            entity_type="decision",
            entity_id=entity_id,
            action=AuditAction.CREATE,
            actor_type="user"
        )
        log2 = AuditLog.objects.create(
            entity_type="decision",
            entity_id=entity_id,
            action=AuditAction.UPDATE,
            actor_type="user"
        )
        log3 = AuditLog.objects.create(
            entity_type="decision",
            entity_id=entity_id,
            action=AuditAction.SUBMIT,
            actor_type="user"
        )
        
        logs = list(AuditLog.objects.for_entity("decision", entity_id))
        
        assert len(logs) == 3
        # Should be ordered by timestamp (newest first or oldest first based on ordering)
        assert logs[0].id == log1.id
        assert logs[1].id == log2.id
        assert logs[2].id == log3.id


@pytest.mark.django_db
class TestAuditLogImmutability:
    """Test that audit logs are effectively immutable."""

    def test_audit_log_cannot_be_modified_after_creation(self, audit_log_data):
        """
        Should prevent modification of critical fields after creation.
        
        Critical fields (entity_type, entity_id, action, timestamp) cannot
        be modified. This is enforced at the model save() level.
        """
        entity_id = uuid.uuid4()
        audit_log = AuditLog.objects.create(
            entity_type="decision",
            entity_id=entity_id,
            action=AuditAction.CREATE,
            actor_type="user",
            current_state={"status": "draft"}
        )
        
        # Try to modify critical fields - should raise ValueError
        audit_log.entity_type = "workflow"
        
        with pytest.raises(ValueError) as exc_info:
            audit_log.save()
        
        assert "Cannot modify entity_type" in str(exc_info.value)
        
        # Verify original record is unchanged
        audit_log.refresh_from_db()
        assert audit_log.entity_type == "decision"
    
    def test_audit_log_entity_id_cannot_be_modified(self, audit_log_data):
        """
        Should prevent modification of entity_id after creation.
        """
        original_entity_id = uuid.uuid4()
        audit_log = AuditLog.objects.create(
            entity_type="decision",
            entity_id=original_entity_id,
            action=AuditAction.CREATE,
            actor_type="user"
        )
        
        audit_log.entity_id = uuid.uuid4()
        
        with pytest.raises(ValueError) as exc_info:
            audit_log.save()
        
        assert "Cannot modify entity_id" in str(exc_info.value)
        
        audit_log.refresh_from_db()
        assert audit_log.entity_id == original_entity_id
    
    def test_audit_log_action_cannot_be_modified(self, audit_log_data):
        """
        Should prevent modification of action after creation.
        """
        audit_log = AuditLog.objects.create(
            entity_type="decision",
            entity_id=uuid.uuid4(),
            action=AuditAction.CREATE,
            actor_type="user"
        )
        
        audit_log.action = AuditAction.UPDATE
        
        with pytest.raises(ValueError) as exc_info:
            audit_log.save()
        
        assert "Cannot modify action" in str(exc_info.value)
        
        audit_log.refresh_from_db()
        assert audit_log.action == AuditAction.CREATE
    
    def test_audit_log_non_critical_fields_can_be_modified(self, audit_log_data):
        """
        Should allow modification of non-critical fields.
        
        Metadata and current_state can be updated for audit trail corrections.
        """
        audit_log = AuditLog.objects.create(
            entity_type="decision",
            entity_id=uuid.uuid4(),
            action=AuditAction.CREATE,
            actor_type="user",
            metadata={"source": "api"},
            current_state={"status": "draft"}
        )
        
        # These should be allowed
        audit_log.metadata = {"source": "api", "corrected": True}
        audit_log.current_state = {"status": "pending"}
        audit_log.save()
        
        audit_log.refresh_from_db()
        assert audit_log.metadata == {"source": "api", "corrected": True}
        assert audit_log.current_state == {"status": "pending"}
