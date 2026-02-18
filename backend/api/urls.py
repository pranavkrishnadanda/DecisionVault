"""
API module URL configuration.

Provides REST API endpoints for DecisionVault.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from decisions.views import DecisionViewSet
from api.views import health


app_name = "api"

# DRF Router for ViewSets
router = DefaultRouter()
router.register(r"decisions", DecisionViewSet, basename="decision")

urlpatterns = [
    path("", include(router.urls)),
    path("health/", health, name="health"),
]
