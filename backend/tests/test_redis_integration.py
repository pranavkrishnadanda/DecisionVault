"""
Integration tests for Redis cache connectivity.

These tests verify that Redis is properly configured and accessible.
They require Redis to be running on the configured host/port.

Run with: pytest tests/test_redis_integration.py -v
"""

import pytest
import redis
from django.core.cache import cache
from django.conf import settings


class TestRedisConnection:
    """Test Redis connectivity and configuration."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Clear cache before and after each test."""
        cache.clear()
        yield
        cache.clear()

    def test_redis_settings_configured(self):
        """
        Redis settings must be properly configured.
        """
        assert hasattr(settings, "REDIS_HOST")
        assert hasattr(settings, "REDIS_PORT")
        assert isinstance(settings.REDIS_PORT, int)

    def test_redis_cache_backend_is_redis(self):
        """
        Cache backend must be Redis.
        """
        backend = settings.CACHES["default"]["BACKEND"]
        assert "redis" in backend.lower()

    def test_redis_connection_ping(self):
        """
        Redis server should respond to PING.
        
        This test will fail if Redis is not running.
        """
        client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=1,  # Test DB
        )
        try:
            assert client.ping() is True
        except redis.ConnectionError as e:
            pytest.fail(f"Redis connection failed: {e}")

    def test_redis_cache_set_get(self):
        """
        Cache should support basic set/get operations.
        """
        cache.set("test_key", "test_value", timeout=60)
        value = cache.get("test_key")
        assert value == "test_value"

    def test_redis_cache_delete(self):
        """
        Cache should support delete operations.
        """
        cache.set("to_delete", "value", timeout=60)
        assert cache.get("to_delete") == "value"
        
        cache.delete("to_delete")
        assert cache.get("to_delete") is None

    def test_redis_cache_expiration(self):
        """
        Cache should support key expiration.
        """
        cache.set("expiring_key", "value", timeout=1)
        assert cache.get("expiring_key") == "value"
        
        # Wait for expiration
        import time
        time.sleep(1.5)
        
        assert cache.get("expiring_key") is None

    def test_redis_cache_get_or_set(self):
        """
        Cache should support get_or_set pattern.
        """
        # First call sets the value
        value = cache.get_or_set("lazy_key", "default_value", timeout=60)
        assert value == "default_value"
        
        # Second call returns cached value
        value = cache.get_or_set("lazy_key", "other_value", timeout=60)
        assert value == "default_value"

    def test_redis_cache_clear(self):
        """
        Cache clear should remove all keys.
        """
        cache.set("key1", "value1", timeout=60)
        cache.set("key2", "value2", timeout=60)
        
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestRedisCacheLocation:
    """Test Redis cache location configuration."""

    def test_cache_location_uses_env_host(self):
        """
        Cache location should use REDIS_HOST from environment.
        """
        location = settings.CACHES["default"]["LOCATION"]
        assert settings.REDIS_HOST in location

    def test_cache_location_uses_env_port(self):
        """
        Cache location should use REDIS_PORT from environment.
        """
        location = settings.CACHES["default"]["LOCATION"]
        assert str(settings.REDIS_PORT) in location
