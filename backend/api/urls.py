"""
API module URL configuration.

Provides REST API endpoints for DecisionVault.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from api.views import (
    IntegrationViewSet,
    OrganizationTokenObtainPairView,
    RegisterView,
    SavedViewViewSet,
    TablePreferenceDetailView,
    WebhookDeliveryViewSet,
    WebhookSubscriptionViewSet,
    health,
)
from decisions.views import DecisionViewSet

app_name = "api"

# DRF Router for ViewSets
router = DefaultRouter()
router.register(r"decisions", DecisionViewSet, basename="decision")
router.register(r"saved-views", SavedViewViewSet, basename="saved-view")
router.register(r"integrations", IntegrationViewSet, basename="integration")
router.register(
    r"webhook-subscriptions",
    WebhookSubscriptionViewSet,
    basename="webhook-subscription",
)
router.register(
    r"webhook-deliveries",
    WebhookDeliveryViewSet,
    basename="webhook-delivery",
)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "table-preferences/<str:table>/",
        TablePreferenceDetailView.as_view(),
        name="table_preferences_detail",
    ),
    path("health/", health, name="health"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path(
        "auth/token/",
        OrganizationTokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
