"""API serializers for auth and utility endpoints."""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import serializers

from decisions.models import DecisionStatus, SavedView

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
