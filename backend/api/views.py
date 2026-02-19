from datetime import timedelta

from django.contrib.auth import authenticate
from django.core import signing
from django.http import JsonResponse
from django.utils import timezone
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from api.models import (
    INTEGRATION_EVENT_TYPES,
    Integration,
    IntegrationTrigger,
    WebhookDelivery,
    WebhookSubscription,
)
from api.serializers import (
    IntegrationSerializer,
    RegisterSerializer,
    SavedViewSerializer,
    TablePreferenceSerializer,
    WebhookDeliveryDetailSerializer,
    WebhookDeliveryListSerializer,
    WebhookSubscriptionSerializer,
)
from api.services.auth_tokens import (
    REFRESH_COOKIE_NAME,
    issue_session_tokens,
    refresh_cookie_options,
    revoke_refresh_token,
    rotate_refresh_token,
)
from api.services.credentials_vault import encrypt_credentials
from api.services.integration_oauth import (
    build_slack_install_url,
    exchange_slack_oauth_code,
)
from api.services.webhook_dispatcher import replay_webhook_delivery
from api.services.webhook_observability import (
    build_delivery_timeline,
    compute_webhook_metrics,
    force_retry_delivery,
    reactivate_webhook_subscription,
)
from core.permissions import (
    get_user_membership_or_raise,
    require_read_role,
    require_write_role,
    scope_queryset_to_membership,
)
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
        access_token, refresh_token = issue_session_tokens(user=user)

        response = Response(
            {
                "access": access_token,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                },
            },
            status=status.HTTP_201_CREATED,
        )
        response.set_cookie(
            REFRESH_COOKIE_NAME,
            refresh_token,
            **refresh_cookie_options(),
        )
        return response


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username", "")
        password = request.data.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response(
                {"detail": "No active account found with the given credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        access_token, refresh_token = issue_session_tokens(user=user)
        response = Response({"access": access_token}, status=status.HTTP_200_OK)
        response.set_cookie(
            REFRESH_COOKIE_NAME,
            refresh_token,
            **refresh_cookie_options(),
        )
        return response


class RefreshSessionView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_cookie = request.COOKIES.get(REFRESH_COOKIE_NAME, "")
        rotated = rotate_refresh_token(raw_token=refresh_cookie)
        if rotated is None:
            response = Response(
                {"detail": "Session refresh failed."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            response.delete_cookie(REFRESH_COOKIE_NAME, path="/", samesite="Lax")
            return response

        access_token, refresh_token = rotated
        response = Response({"access": access_token}, status=status.HTTP_200_OK)
        response.set_cookie(
            REFRESH_COOKIE_NAME,
            refresh_token,
            **refresh_cookie_options(),
        )
        return response


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_cookie = request.COOKIES.get(REFRESH_COOKIE_NAME, "")
        revoke_refresh_token(raw_token=refresh_cookie)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(REFRESH_COOKIE_NAME, path="/", samesite="Lax")
        return response


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


class WebhookSubscriptionViewSet(ModelViewSet):
    """Organization-scoped webhook subscription CRUD."""

    serializer_class = WebhookSubscriptionSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "delete"]

    def get_queryset(self):
        membership = get_user_membership_or_raise(self.request.user)
        require_read_role(membership)
        queryset = WebhookSubscription.objects.select_related(
            "organization", "created_by"
        )
        return scope_queryset_to_membership(queryset, membership).order_by(
            "-created_at"
        )

    def perform_create(self, serializer):
        membership = get_user_membership_or_raise(self.request.user)
        require_write_role(membership)
        serializer.save(
            organization=membership.organization,
            created_by=self.request.user,
        )

    def perform_update(self, serializer):
        membership = get_user_membership_or_raise(self.request.user)
        require_write_role(membership)
        serializer.save()

    def perform_destroy(self, instance):
        membership = get_user_membership_or_raise(self.request.user)
        require_write_role(membership)
        instance.delete()

    @action(detail=True, methods=["post"], url_path="reactivate")
    def reactivate(self, request, pk=None):
        membership = get_user_membership_or_raise(request.user)
        require_write_role(membership)
        subscription = self.get_object()
        actor_id = str(request.user.id) if request.user and request.user.id else ""
        reactivate_webhook_subscription(subscription=subscription, actor_id=actor_id)

        serializer = WebhookSubscriptionSerializer(subscription)
        return Response(serializer.data, status=status.HTTP_200_OK)


class WebhookDeliveryPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class WebhookDeliveryViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
):
    """Organization-scoped webhook delivery read/replay API."""

    permission_classes = [IsAuthenticated]
    serializer_class = WebhookDeliveryListSerializer
    pagination_class = WebhookDeliveryPagination
    http_method_names = ["get", "post"]

    def get_queryset(self):
        membership = get_user_membership_or_raise(self.request.user)
        require_read_role(membership)
        queryset = WebhookDelivery.objects.select_related(
            "organization", "subscription"
        ).order_by("-created_at")
        if self.action == "retrieve":
            queryset = queryset.prefetch_related("attempts")
        return scope_queryset_to_membership(queryset, membership)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return WebhookDeliveryDetailSerializer
        return WebhookDeliveryListSerializer

    @action(detail=False, methods=["get"], url_path="metrics")
    def metrics(self, request):
        membership = get_user_membership_or_raise(request.user)
        require_read_role(membership)
        payload = compute_webhook_metrics(organization=membership.organization)
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="timeline")
    def timeline(self, request, pk=None):
        membership = get_user_membership_or_raise(request.user)
        require_read_role(membership)
        delivery = self.get_object()
        payload = build_delivery_timeline(delivery=delivery)
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="replay")
    def replay(self, request, pk=None):
        membership = get_user_membership_or_raise(request.user)
        require_write_role(membership)
        delivery = self.get_object()

        if delivery.status != WebhookDelivery.Status.FAILED:
            raise ValidationError({"status": "Only failed deliveries can be replayed."})

        replay_webhook_delivery(delivery)
        delivery.refresh_from_db()

        serializer = WebhookDeliveryDetailSerializer(delivery)
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"], url_path="force-retry")
    def force_retry(self, request, pk=None):
        membership = get_user_membership_or_raise(request.user)
        require_write_role(membership)
        delivery = self.get_object()

        if delivery.status != WebhookDelivery.Status.FAILED:
            raise ValidationError({"status": "Only failed deliveries can be replayed."})

        actor_id = str(request.user.id) if request.user and request.user.id else ""
        force_retry_delivery(delivery=delivery, actor_id=actor_id)
        delivery.refresh_from_db()
        serializer = WebhookDeliveryDetailSerializer(delivery)
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)


class IntegrationViewSet(ModelViewSet):
    """Organization-scoped integrations CRUD + OAuth helpers."""

    serializer_class = IntegrationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "delete"]

    def get_queryset(self):
        membership = get_user_membership_or_raise(self.request.user)
        require_read_role(membership)
        queryset = Integration.objects.select_related("organization", "created_by")
        queryset = queryset.prefetch_related("triggers")
        return scope_queryset_to_membership(queryset, membership).order_by(
            "-created_at"
        )

    def perform_create(self, serializer):
        membership = get_user_membership_or_raise(self.request.user)
        require_write_role(membership)

        credentials = serializer.validated_data.pop("credentials", {})
        triggers = serializer.validated_data.pop("triggers", [])
        integration = serializer.save(
            organization=membership.organization,
            created_by=self.request.user,
            credentials_encrypted=encrypt_credentials(credentials),
        )

        trigger_rows = []
        for item in triggers:
            if item["event_type"] not in INTEGRATION_EVENT_TYPES:
                continue
            trigger_rows.append(
                IntegrationTrigger(
                    organization=membership.organization,
                    integration=integration,
                    event_type=item["event_type"],
                    message_template=item.get("message_template", ""),
                    is_active=item.get("is_active", True),
                )
            )
        if trigger_rows:
            IntegrationTrigger.objects.bulk_create(trigger_rows)

    def perform_update(self, serializer):
        membership = get_user_membership_or_raise(self.request.user)
        require_write_role(membership)

        credentials = serializer.validated_data.pop("credentials", None)
        integration = serializer.save()
        if credentials is not None:
            integration.credentials_encrypted = encrypt_credentials(credentials)
            integration.save(update_fields=["credentials_encrypted", "updated_at"])

    def perform_destroy(self, instance):
        membership = get_user_membership_or_raise(self.request.user)
        require_write_role(membership)
        instance.delete()

    @action(detail=True, methods=["get"], url_path="slack/install-url")
    def slack_install_url(self, request, pk=None):
        membership = get_user_membership_or_raise(request.user)
        require_write_role(membership)
        integration = self.get_object()
        if integration.connector_type != Integration.ConnectorType.SLACK:
            raise ValidationError({"connector_type": "Integration is not Slack."})

        redirect_uri = request.query_params.get("redirect_uri")
        if not redirect_uri:
            raise ValidationError({"redirect_uri": "redirect_uri is required."})

        state = signing.dumps(
            {
                "integration_id": str(integration.id),
                "organization_id": str(membership.organization_id),
            },
            salt="slack_oauth_state",
        )
        install_url = build_slack_install_url(state=state, redirect_uri=redirect_uri)
        return Response({"install_url": install_url}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="slack/oauth-callback")
    def slack_oauth_callback(self, request, pk=None):
        membership = get_user_membership_or_raise(request.user)
        require_write_role(membership)
        integration = self.get_object()
        if integration.connector_type != Integration.ConnectorType.SLACK:
            raise ValidationError({"connector_type": "Integration is not Slack."})

        code = request.data.get("code")
        redirect_uri = request.data.get("redirect_uri")
        if not code or not redirect_uri:
            raise ValidationError(
                {"detail": "code and redirect_uri are required for OAuth callback."}
            )

        tokens = exchange_slack_oauth_code(code=code, redirect_uri=redirect_uri)
        credentials = {
            "access_token": tokens.get("access_token", ""),
            "refresh_token": tokens.get("refresh_token", ""),
        }
        integration.credentials_encrypted = encrypt_credentials(credentials)
        expires_in = int(tokens.get("expires_in", 0) or 0)
        integration.token_expires_at = (
            timezone.now() + timedelta(seconds=expires_in) if expires_in > 0 else None
        )
        integration.last_error = ""
        integration.save(
            update_fields=[
                "credentials_encrypted",
                "token_expires_at",
                "last_error",
                "updated_at",
            ]
        )

        serializer = self.get_serializer(integration)
        return Response(serializer.data, status=status.HTTP_200_OK)


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
