"""API serializers for auth and utility endpoints."""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from api.models import (
    INTEGRATION_EVENT_TYPES,
    WEBHOOK_EVENT_TYPES,
    Integration,
    IntegrationDelivery,
    IntegrationDeliveryAttempt,
    IntegrationTrigger,
    OrganizationMembership,
    WebhookDelivery,
    WebhookDeliveryAttempt,
    WebhookSubscription,
)
from decisions.models import DecisionStatus, SavedView, TableDensity, TablePreference

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    """Serializer for self-service user registration."""

    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_username(self, value: str) -> str:
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists")
        return value

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def create(self, validated_data: dict):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )
        return user


def inject_access_context_claims(token, user) -> None:
    membership = (
        OrganizationMembership.objects.select_related("organization")
        .filter(user=user)
        .order_by("created_at")
        .first()
    )
    if membership is None:
        return

    token["organization_id"] = str(membership.organization_id)
    token["role"] = membership.role


class OrganizationTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        inject_access_context_claims(token, user)
        return token


class SavedViewSerializer(serializers.ModelSerializer):
    """Serializer for user-owned decision filter presets."""

    ALLOWED_FILTER_KEYS = {"q", "status", "from", "to", "limit", "offset"}

    class Meta:
        model = SavedView
        fields = ["id", "name", "filters", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_filters(self, value: dict):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Filters must be an object.")

        unknown = set(value.keys()) - self.ALLOWED_FILTER_KEYS
        if unknown:
            raise serializers.ValidationError("Filters contain unsupported keys.")

        status_value = value.get("status")
        if status_value is not None:
            if not isinstance(status_value, str):
                raise serializers.ValidationError("status must be a string.")
            valid_statuses = {choice for choice, _ in DecisionStatus.choices}
            statuses = [
                item.strip() for item in status_value.split(",") if item.strip()
            ]
            if not statuses or any(item not in valid_statuses for item in statuses):
                raise serializers.ValidationError("status filter is invalid.")

        q_value = value.get("q")
        if q_value is not None and not isinstance(q_value, str):
            raise serializers.ValidationError("q must be a string.")

        for date_key in ("from", "to"):
            date_value = value.get(date_key)
            if date_value is None:
                continue
            if not isinstance(date_value, str):
                raise serializers.ValidationError(f"{date_key} must be a string.")
            if parse_datetime(date_value) is None and parse_date(date_value) is None:
                raise serializers.ValidationError(
                    f"{date_key} must be ISO date/datetime."
                )

        for int_key in ("limit", "offset"):
            int_value = value.get(int_key)
            if int_value is None:
                continue
            if not isinstance(int_value, int):
                raise serializers.ValidationError(f"{int_key} must be an integer.")
            if int_value < 0:
                raise serializers.ValidationError(f"{int_key} must be >= 0.")

        return value


class TablePreferenceSerializer(serializers.ModelSerializer):
    """Serializer for per-user operator table preferences."""

    ALLOWED_TABLES = {"decisions"}
    ALLOWED_COLUMNS_BY_TABLE = {
        "decisions": ("id", "workflow", "status", "updated"),
    }

    class Meta:
        model = TablePreference
        fields = [
            "id",
            "table",
            "visible_columns",
            "column_order",
            "density",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "table", "created_at", "updated_at"]

    def validate(self, attrs):
        table_name = attrs.get("table") or getattr(self.instance, "table", None)
        if table_name not in self.ALLOWED_TABLES:
            raise serializers.ValidationError({"table": "Unsupported table."})

        allowed_columns = self.ALLOWED_COLUMNS_BY_TABLE[table_name]
        visible_columns = attrs.get("visible_columns")
        column_order = attrs.get("column_order")

        if not isinstance(visible_columns, list) or not visible_columns:
            raise serializers.ValidationError(
                {"visible_columns": "visible_columns must be a non-empty list."}
            )
        if any(not isinstance(item, str) for item in visible_columns):
            raise serializers.ValidationError(
                {"visible_columns": "visible_columns entries must be strings."}
            )
        if any(item not in allowed_columns for item in visible_columns):
            raise serializers.ValidationError(
                {"visible_columns": "visible_columns contain unsupported values."}
            )
        if len(set(visible_columns)) != len(visible_columns):
            raise serializers.ValidationError(
                {"visible_columns": "visible_columns must not contain duplicates."}
            )

        if not isinstance(column_order, list):
            raise serializers.ValidationError(
                {"column_order": "column_order must be a list."}
            )
        if any(not isinstance(item, str) for item in column_order):
            raise serializers.ValidationError(
                {"column_order": "column_order entries must be strings."}
            )
        if set(column_order) != set(allowed_columns):
            raise serializers.ValidationError(
                {
                    "column_order": "column_order must contain each available column exactly once."
                }
            )

        if not set(visible_columns).issubset(set(column_order)):
            raise serializers.ValidationError(
                {"visible_columns": "visible_columns must be a subset of column_order."}
            )

        density = attrs.get("density")
        valid_densities = {choice for choice, _ in TableDensity.choices}
        if density not in valid_densities:
            raise serializers.ValidationError({"density": "Invalid density."})

        return attrs


class WebhookSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for organization-scoped webhook subscriptions."""

    class Meta:
        model = WebhookSubscription
        fields = [
            "id",
            "target_url",
            "events",
            "is_active",
            "signing_secret",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "signing_secret": {"write_only": True},
        }

    def validate_signing_secret(self, value: str) -> str:
        if not isinstance(value, str) or len(value.strip()) < 12:
            raise serializers.ValidationError(
                "signing_secret must be at least 12 characters."
            )
        return value.strip()

    def validate_events(self, value: list[str]) -> list[str]:
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError("events must be a non-empty list.")
        if any(not isinstance(item, str) for item in value):
            raise serializers.ValidationError("events entries must be strings.")

        allowed = set(WEBHOOK_EVENT_TYPES)
        unknown = [event for event in value if event not in allowed]
        if unknown:
            raise serializers.ValidationError("events contain unsupported values.")

        normalized = list(dict.fromkeys(value))
        return normalized


class IntegrationTriggerSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationTrigger
        fields = [
            "id",
            "event_type",
            "message_template",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_event_type(self, value: str) -> str:
        if value not in INTEGRATION_EVENT_TYPES:
            raise serializers.ValidationError("Unsupported event_type.")
        return value


class IntegrationSerializer(serializers.ModelSerializer):
    credentials = serializers.JSONField(write_only=True, required=False)
    triggers = IntegrationTriggerSerializer(many=True, required=False)

    class Meta:
        model = Integration
        fields = [
            "id",
            "name",
            "connector_type",
            "config",
            "credentials",
            "token_expires_at",
            "is_active",
            "last_error",
            "triggers",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "token_expires_at",
            "last_error",
            "created_at",
            "updated_at",
        ]

    def validate_connector_type(self, value: str) -> str:
        valid = {choice for choice, _ in Integration.ConnectorType.choices}
        if value not in valid:
            raise serializers.ValidationError("Unsupported connector_type.")
        return value

    def validate(self, attrs):
        connector_type = attrs.get("connector_type") or getattr(
            self.instance, "connector_type", None
        )
        config = attrs.get("config", getattr(self.instance, "config", {}))
        if not isinstance(config, dict):
            raise serializers.ValidationError({"config": "config must be an object."})

        if connector_type == Integration.ConnectorType.SLACK:
            if not config.get("channel_id"):
                raise serializers.ValidationError(
                    {"config": "Slack connector requires channel_id."}
                )
        elif connector_type == Integration.ConnectorType.TEAMS:
            if not config.get("message_template"):
                raise serializers.ValidationError(
                    {"config": "Teams connector requires message_template."}
                )
        elif connector_type == Integration.ConnectorType.EMAIL:
            required = ("smtp_host", "from_email", "to_email")
            missing = [key for key in required if not config.get(key)]
            if missing:
                raise serializers.ValidationError(
                    {"config": f"Email connector missing: {', '.join(missing)}"}
                )

        return attrs


class WebhookDeliverySubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookSubscription
        fields = ["id", "target_url", "is_active"]


class WebhookDeliveryAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookDeliveryAttempt
        fields = [
            "id",
            "attempt_number",
            "status",
            "response_status",
            "response_request_id",
            "error_message",
            "created_at",
        ]


class WebhookDeliveryListSerializer(serializers.ModelSerializer):
    subscription = WebhookDeliverySubscriptionSerializer(read_only=True)

    class Meta:
        model = WebhookDelivery
        fields = [
            "id",
            "event_type",
            "status",
            "attempt_count",
            "max_attempts",
            "last_attempt_at",
            "next_retry_at",
            "last_response_status",
            "last_error",
            "created_at",
            "updated_at",
            "subscription",
        ]


class WebhookDeliveryDetailSerializer(WebhookDeliveryListSerializer):
    attempts = WebhookDeliveryAttemptSerializer(many=True, read_only=True)

    class Meta(WebhookDeliveryListSerializer.Meta):
        fields = WebhookDeliveryListSerializer.Meta.fields + [
            "payload",
            "attempts",
        ]


class IntegrationDeliveryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationDelivery
        fields = [
            "id",
            "event_type",
            "status",
            "attempt_count",
            "max_attempts",
            "last_attempt_at",
            "next_retry_at",
            "last_response_status",
            "last_error",
            "created_at",
            "updated_at",
        ]


class IntegrationDeliveryIntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Integration
        fields = ["id", "name", "connector_type", "is_active"]


class IntegrationDeliveryAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationDeliveryAttempt
        fields = [
            "id",
            "attempt_number",
            "status",
            "response_status",
            "error_message",
            "created_at",
        ]


class IntegrationDeliveryDetailSerializer(IntegrationDeliveryListSerializer):
    integration = IntegrationDeliveryIntegrationSerializer(read_only=True)
    attempts = IntegrationDeliveryAttemptSerializer(many=True, read_only=True)

    class Meta(IntegrationDeliveryListSerializer.Meta):
        fields = IntegrationDeliveryListSerializer.Meta.fields + [
            "payload",
            "integration",
            "attempts",
        ]
