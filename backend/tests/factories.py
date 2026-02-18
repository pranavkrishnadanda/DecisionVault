"""
Factory Boy factories for DecisionVault models.

Usage:
    decision = DecisionFactory()
    workflow = WorkflowFactory(decision=decision)
    step = WorkflowStepFactory(workflow=workflow)
    audit_log = AuditLogFactory(entity=decision)
"""

import factory
from factory.django import DjangoModelFactory
from factory import Faker, post_generation
import uuid


class DecisionFactory(DjangoModelFactory):
    """Factory for Decision model."""
    
    class Meta:
        model = "decisions.Decision"
    
    id = factory.LazyFunction(uuid.uuid4)
    title = Faker("sentence", nb_words=4)
    description = Faker("paragraph")
    status = "draft"
    priority = Faker("random_int", min=-10, max=10)
    created_by = Faker("uuid4")
    metadata = factory.Dict({
        "test": True,
        "source": "factory_boy"
    })
    
    @post_generation
    def set_workflow_started_at(obj, create, extracted, **kwargs):
        if extracted:
            obj.workflow_started_at = extracted
    
    @post_generation
    def set_workflow_completed_at(obj, create, extracted, **kwargs):
        if extracted:
            obj.workflow_completed_at = extracted


class WorkflowFactory(DjangoModelFactory):
    """Factory for Workflow model."""
    
    class Meta:
        model = "decisions.Workflow"
    
    id = factory.LazyFunction(uuid.uuid4)
    decision = factory.SubFactory(DecisionFactory)
    status = "pending"
    name = Faker("sentence", nb_words=3)
    description = Faker("paragraph")
    timeout_sec = 300
    max_retries = 3


class WorkflowStepFactory(DjangoModelFactory):
    """Factory for WorkflowStep model."""
    
    class Meta:
        model = "decisions.WorkflowStep"
    
    id = factory.LazyFunction(uuid.uuid4)
    workflow = factory.SubFactory(WorkflowFactory)
    step_number = factory.Sequence(lambda n: n)
    agent_type = "schema_validator"
    action = "validate_schema"
    status = "pending"
    timeout_sec = 60
    max_retries = 3
    retry_count = 0


class AuditLogFactory(DjangoModelFactory):
    """Factory for AuditLog model."""
    
    class Meta:
        model = "decisions.AuditLog"
    
    id = factory.LazyFunction(uuid.uuid4)
    entity_type = "decision"
    entity_id = factory.LazyFunction(uuid.uuid4)
    action = "create"
    actor_type = "user"
    actor_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    previous_state = None
    current_state = factory.Dict({"status": "draft"})
    metadata = factory.Dict({"source": "test"})
