"""
Tests for Django application registration.

Verifies that all DecisionVault modules are properly registered
in INSTALLED_APPS and have valid app configurations.
"""

import pytest
from django.conf import settings
from django.apps import apps


class TestModuleRegistration:
    """Test that all DecisionVault modules are registered."""

    REQUIRED_APPS = [
        "api",
        "ingestion",
        "verification",
        "workers",
    ]

    @pytest.mark.parametrize("app_name", REQUIRED_APPS)
    def test_app_in_installed_apps(self, app_name):
        """
        Each required app must be in INSTALLED_APPS.
        
        Without registration, Django won't:
        - Load the app's models
        - Process the app's URL patterns
        - Run the app's migrations
        """
        assert app_name in settings.INSTALLED_APPS, (
            f"App '{app_name}' not found in INSTALLED_APPS. "
            f"Current apps: {settings.INSTALLED_APPS}"
        )

    def test_all_required_apps_are_importable(self):
        """
        All required apps must be importable Python packages.
        
        This ensures the app structure is valid.
        """
        for app_name in self.REQUIRED_APPS:
            __import__(app_name)

    def test_apps_have_valid_configs(self):
        """
        All registered apps must have valid AppConfig classes.
        
        Django requires apps to have either:
        - A default_app_config attribute, or
        - An apps.py with an AppConfig subclass
        """
        for app_name in self.REQUIRED_APPS:
            # This will raise LookupError if app is not properly configured
            app_config = apps.get_app_config(app_name)
            assert app_config is not None
            assert hasattr(app_config, "name")

    def test_core_app_is_registered(self):
        """
        Core app should be registered (implicit via settings module).
        
        This validates the base Django configuration is intact.
        """
        # Core is implicitly registered as the settings module
        # We verify by checking that core settings are loaded
        assert hasattr(settings, "BASE_DIR")
        # Verify BASE_DIR points to the backend project directory
        assert settings.BASE_DIR.name == "backend"
