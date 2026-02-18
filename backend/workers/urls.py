"""
Workers module URL configuration.

Provides endpoints for worker management and job status.
"""

from django.urls import path
from . import views


app_name = "workers"

urlpatterns = [
    path("", views.base, name="workers-base"),
]
