"""
Pytest fixtures and configuration for DecisionVault.

Provides shared fixtures for integration and unit tests.
"""

import pytest
import uuid
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


@pytest.fixture(scope="session")
def django_db_setup():
    """
    Configure database for tests.
    
    pytest-django handles database creation/teardown automatically.
    This fixture ensures proper ordering if needed.
    """
    pass


@pytest.fixture
def test_user(django_user_model):
    """Create a test user."""
    return django_user_model.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123"
    )


@pytest.fixture
def authenticated_client(client, test_user):
    """Create an authenticated test client."""
    client.force_login(test_user)
    return client


@pytest.fixture(scope="session")
def redis_host():
    """Return Redis host from settings."""
    return getattr(settings, "REDIS_HOST", "localhost")


@pytest.fixture(scope="session")
def redis_port():
    """Return Redis port from settings."""
    return getattr(settings, "REDIS_PORT", 6379)


@pytest.fixture(scope="session")
def rabbitmq_host():
    """Return RabbitMQ host from settings."""
    return getattr(settings, "RABBITMQ_HOST", "localhost")


@pytest.fixture(scope="session")
def rabbitmq_port():
    """Return RabbitMQ port from settings."""
    return getattr(settings, "RABBITMQ_PORT", 5672)


# Model test fixtures

@pytest.fixture
def decision_data():
    """Base decision test data."""
    return {
        "title": "Test Decision",
        "description": "A test decision for unit testing",
        "priority": 5,
        "created_by": "user_123",
        "metadata": {
            "customer_id": "cust_456",
            "amount": 50000,
            "product": "personal_loan"
        }
    }


@pytest.fixture
def workflow_data():
    """Base workflow test data."""
    return {
        "name": "Test Workflow",
        "description": "A test workflow",
        "timeout_sec": 300,
        "max_retries": 3
    }


@pytest.fixture
def workflow_step_data():
    """Base workflow step test data."""
    return {
        "step_number": 1,
        "agent_type": "schema_validator",
        "action": "validate_schema",
        "timeout_sec": 60,
        "max_retries": 3
    }


@pytest.fixture
def audit_log_data():
    """Base audit log test data."""
    return {
        "entity_type": "decision",
        "action": "create",
        "actor_type": "user",
        "actor_id": "user_123",
        "previous_state": None,
        "current_state": {"status": "draft"},
        "metadata": {"source": "api"}
    }
