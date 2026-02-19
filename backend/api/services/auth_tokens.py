"""Persistent refresh-token session management for auth continuity."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken as JwtRefreshToken

from api.models import OrganizationMembership, RefreshToken

REFRESH_COOKIE_NAME = "dv_refresh"
REFRESH_TTL_DAYS = 30

User = get_user_model()


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _build_access_token(
    *, user: User, organization_id: uuid.UUID, role: str
) -> str:
    refresh = JwtRefreshToken.for_user(user)
    access = refresh.access_token
    access["organization_id"] = str(organization_id)
    access["role"] = role
    return str(access)


def _create_refresh_token_record(*, user: User, organization_id: uuid.UUID) -> tuple[RefreshToken, str]:
    token_id = uuid.uuid4()
    token_secret = secrets.token_urlsafe(48)
    raw_token = f"{token_id}.{token_secret}"

    row = RefreshToken.objects.create(
        id=token_id,
        user=user,
        organization_id=organization_id,
        hashed_token=hash_refresh_token(raw_token),
        expires_at=timezone.now() + timedelta(days=REFRESH_TTL_DAYS),
        revoked=False,
    )
    return row, raw_token


def issue_session_tokens(*, user: User) -> tuple[str, str]:
    membership = (
        OrganizationMembership.objects.select_related("organization")
        .filter(user=user)
        .order_by("created_at")
        .first()
    )
    if membership is None:
        raise ValueError("No organization membership.")

    access_token = _build_access_token(
        user=user,
        organization_id=membership.organization_id,
        role=membership.role,
    )
    _row, refresh_token = _create_refresh_token_record(
        user=user,
        organization_id=membership.organization_id,
    )
    return access_token, refresh_token


def rotate_refresh_token(*, raw_token: str) -> tuple[str, str] | None:
    if not raw_token:
        return None

    token_parts = raw_token.split(".", 1)
    if len(token_parts) != 2:
        return None

    token_id_raw = token_parts[0]
    try:
        token_id = uuid.UUID(token_id_raw)
    except ValueError:
        return None

    row = (
        RefreshToken.objects.select_related("user", "organization")
        .filter(id=token_id)
        .first()
    )
    if row is None or row.revoked:
        return None

    if row.expires_at <= timezone.now():
        row.revoked = True
        row.save(update_fields=["revoked", "updated_at"])
        return None

    if not hmac.compare_digest(row.hashed_token, hash_refresh_token(raw_token)):
        return None

    membership = (
        OrganizationMembership.objects.filter(
            user=row.user,
            organization=row.organization,
        )
        .order_by("created_at")
        .first()
    )
    if membership is None:
        row.revoked = True
        row.save(update_fields=["revoked", "updated_at"])
        return None

    row.revoked = True
    row.save(update_fields=["revoked", "updated_at"])

    access_token = _build_access_token(
        user=row.user,
        organization_id=row.organization_id,
        role=membership.role,
    )
    _new_row, new_refresh_token = _create_refresh_token_record(
        user=row.user,
        organization_id=row.organization_id,
    )
    return access_token, new_refresh_token


def revoke_refresh_token(*, raw_token: str) -> None:
    if not raw_token:
        return

    token_parts = raw_token.split(".", 1)
    if len(token_parts) != 2:
        return

    try:
        token_id = uuid.UUID(token_parts[0])
    except ValueError:
        return

    row = RefreshToken.objects.filter(id=token_id).first()
    if row is None:
        return

    if hmac.compare_digest(row.hashed_token, hash_refresh_token(raw_token)):
        row.revoked = True
        row.save(update_fields=["revoked", "updated_at"])


def refresh_cookie_options() -> dict:
    secure_default = not getattr(settings, "DEBUG", False)
    return {
        "httponly": True,
        "secure": bool(getattr(settings, "AUTH_COOKIE_SECURE", secure_default)),
        "samesite": "Lax",
        "path": "/",
        "max_age": REFRESH_TTL_DAYS * 24 * 60 * 60,
    }
