import json

from django.http import JsonResponse
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken

from api.serializers import (
    RegisterSerializer,
    SavedViewSerializer,
    TablePreferenceSerializer,
)
from core.permissions import get_user_membership_or_raise, scope_queryset_to_membership
from decisions.models import (
    SavedView,
    TableDensity,
    TablePreference,
    default_decisions_column_order,
    default_decisions_columns,
)


def health(request):
    """
    Health check endpoint for load balancers and monitoring.

    Returns:
        JSON response with status and version information.
    """
    return JsonResponse(
        {
            "status": "ok",
            "version": "0.1.0",
        }
    )


class RegisterView(APIView):
    """Self-service registration endpoint for operator users."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class SavedViewViewSet(ModelViewSet):
    """User-scoped saved views for decisions page filter presets."""

    serializer_class = SavedViewSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        membership = get_user_membership_or_raise(self.request.user)
        queryset = scope_queryset_to_membership(SavedView.objects.all(), membership)
        return queryset.filter(user=self.request.user).order_by("name", "-created_at")

    def perform_create(self, serializer):
        membership = get_user_membership_or_raise(self.request.user)
        serializer.save(user=self.request.user, organization=membership.organization)


class TablePreferenceDetailView(APIView):
    """Retrieve and update per-user table preferences."""

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _default_payload(table_name: str) -> dict:
        if table_name == "decisions":
            return {
                "visible_columns": default_decisions_columns(),
                "column_order": default_decisions_column_order(),
                "density": TableDensity.COMFORTABLE,
            }
        raise ValueError("Unsupported table")

    def get(self, request, table: str):
        if table != "decisions":
            return Response(
                {"detail": "Unsupported table."}, status=status.HTTP_404_NOT_FOUND
            )

        defaults = self._default_payload(table)
        membership = get_user_membership_or_raise(request.user)
        preference, _created = TablePreference.objects.get_or_create(
            user=request.user,
            organization=membership.organization,
            table=table,
            defaults=defaults,
        )
        serializer = TablePreferenceSerializer(preference)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, table: str):
        if table != "decisions":
            return Response(
                {"detail": "Unsupported table."}, status=status.HTTP_404_NOT_FOUND
            )

        defaults = self._default_payload(table)
        membership = get_user_membership_or_raise(request.user)
        preference, _created = TablePreference.objects.get_or_create(
            user=request.user,
            organization=membership.organization,
            table=table,
            defaults=defaults,
        )
        payload = dict(request.data)
        payload["table"] = table

        serializer = TablePreferenceSerializer(preference, data=payload)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
