"""
Pytest fixtures and configuration for DecisionVault.

Provides shared fixtures for integration and unit tests.
"""

import pytest
from django.conf import settings


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
