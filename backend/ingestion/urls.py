"""
Ingestion module URL configuration.

Provides endpoints for data ingestion operations.
"""

from django.urls import path
from . import views


app_name = "ingestion"

urlpatterns = [
    path("", views.base, name="ingestion-base"),
]
