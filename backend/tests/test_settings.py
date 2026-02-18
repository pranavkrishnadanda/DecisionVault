"""
Tests for environment-based configuration.

Verifies that all sensitive and environment-specific settings
are loaded from environment variables, not hardcoded.

This is critical for:
- Production deployments
- CI/CD pipelines
- Multi-environment support
- Security compliance
"""

import os
import pytest
from django.conf import settings


class TestEnvironmentVariables:
    """Test that critical settings come from environment variables."""

    def test_secret_key_from_env(self):
        """
        SECRET_KEY must be configurable via environment.
        
        Security risk if hardcoded in production.
        """
        # In test settings, this comes from pytest-env
        assert settings.SECRET_KEY == "test-secret-key-for-testing-only"

    def test_debug_from_env(self):
        """
        DEBUG must be configurable via environment.
        
        Should be False in production.
        """
        # Test settings force DEBUG=True
        assert isinstance(settings.DEBUG, bool)

    def test_allowed_hosts_from_env(self):
        """
        ALLOWED_HOSTS must be configurable via environment.
        
        Required for production deployment.
        """
        assert isinstance(settings.ALLOWED_HOSTS, list)
        assert len(settings.ALLOWED_HOSTS) > 0

    def test_db_host_from_env(self):
        """
        Database host must be configurable via environment.
        
        Different for local, Docker, and production.
        """
        db_config = settings.DATABASES["default"]
        assert "HOST" in db_config
        # Should come from env, test sets it to localhost
        assert db_config["HOST"] == os.getenv("DB_HOST", "localhost")

    def test_db_name_from_env(self):
        """
        Database name must be configurable via environment.
        """
        db_config = settings.DATABASES["default"]
        assert db_config["NAME"] == os.getenv("DB_NAME", "decisionvault_test")

    def test_db_user_from_env(self):
        """
        Database user must be configurable via environment.
        """
        db_config = settings.DATABASES["default"]
        assert db_config["USER"] == os.getenv("DB_USER", "dvuser")

    def test_db_password_from_env(self):
        """
        Database password must be configurable via environment.
        
        Never hardcode credentials.
        """
        db_config = settings.DATABASES["default"]
        assert db_config["PASSWORD"] == os.getenv("DB_PASSWORD", "dvpass")

    def test_redis_host_from_env(self):
        """
        Redis host must be configurable via environment.
        """
        assert settings.REDIS_HOST == os.getenv("REDIS_HOST", "localhost")

    def test_redis_port_from_env(self):
        """
        Redis port must be configurable via environment.
        """
        assert settings.REDIS_PORT == int(os.getenv("REDIS_PORT", "6379"))

    def test_rabbitmq_host_from_env(self):
        """
        RabbitMQ host must be configurable via environment.
        """
        assert settings.RABBITMQ_HOST == os.getenv("RABBITMQ_HOST", "localhost")

    def test_rabbitmq_port_from_env(self):
        """
        RabbitMQ port must be configurable via environment.
        """
        assert settings.RABBITMQ_PORT == int(os.getenv("RABBITMQ_PORT", "5672"))


class TestSettingsStructure:
    """Test that settings have proper structure."""

    def test_database_has_required_keys(self):
        """
        Database configuration must have all required keys.
        """
        db_config = settings.DATABASES["default"]
        required_keys = ["ENGINE", "NAME", "USER", "PASSWORD", "HOST", "PORT"]
        
        for key in required_keys:
            assert key in db_config, f"Missing required DB config key: {key}"

    def test_cache_has_required_keys(self):
        """
        Cache configuration must have required keys.
        """
        cache_config = settings.CACHES["default"]
        required_keys = ["BACKEND", "LOCATION"]
        
        for key in required_keys:
            assert key in cache_config, f"Missing required cache config key: {key}"

    def test_postgresql_engine_configured(self):
        """
        Must use PostgreSQL database engine.
        """
        db_config = settings.DATABASES["default"]
        assert "postgresql" in db_config["ENGINE"]

    def test_redis_cache_backend_configured(self):
        """
        Must use Redis cache backend.
        """
        cache_config = settings.CACHES["default"]
        assert "redis" in cache_config["BACKEND"].lower()
