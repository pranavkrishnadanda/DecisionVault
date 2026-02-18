"""
Verification module URL configuration.

Provides endpoints for verification workflows.
"""

from django.urls import path
from . import views


app_name = "verification"

urlpatterns = [
    path("", views.base, name="verification-base"),
]
