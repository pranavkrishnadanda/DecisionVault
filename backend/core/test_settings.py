"""
Test settings for DecisionVault.

Uses environment variables for all configuration.
Runs with DEBUG=True and in-memory/test database settings.
"""

import os
from .settings import *  # noqa: F401 F403

# Override with test-specific settings
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

SECRET_KEY = os.getenv("SECRET_KEY", "test-secret-key-for-testing-only")

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Test database - use same DB but pytest-django will handle test isolation
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "decisionvault"),
        "USER": os.getenv("DB_USER", "dvuser"),
        "PASSWORD": os.getenv("DB_PASSWORD", "dvpass"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "OPTIONS": {
            "options": "-c search_path=dv,public"  # Use dv schema by default
        },
    }
}

# Redis configuration from environment
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/1",  # Use DB 1 for tests
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# RabbitMQ configuration from environment
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))

# Logging - more verbose for tests
LOGGING["root"]["level"] = "DEBUG"  # noqa: F405
