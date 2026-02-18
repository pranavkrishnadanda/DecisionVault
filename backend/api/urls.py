"""
API module URL configuration.

Provides REST API endpoints for DecisionVault.
"""

from django.urls import path
from . import views


app_name = "api"

urlpatterns = [
    path("health/", views.health, name="health"),
]
