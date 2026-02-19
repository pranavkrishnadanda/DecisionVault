"""Connector implementations for integration delivery engine."""

from __future__ import annotations

import smtplib
from datetime import timedelta
from email.message import EmailMessage

import httpx
from django.conf import settings
from django.utils import timezone

from api.models import Integration
from api.services.credentials_vault import decrypt_credentials, encrypt_credentials


def _render_template(template: str, *, event_type: str, payload: dict) -> str:
    text = template or "{{event_type}}"
    text = text.replace("{{event_type}}", event_type)
    text = text.replace("{{payload}}", str(payload))
    if "decision_id" in payload:
        text = text.replace("{{payload.decision_id}}", str(payload["decision_id"]))
    return text


def refresh_slack_access_token(integration: Integration) -> dict:
    credentials = decrypt_credentials(integration.credentials_encrypted)
    refresh_token = credentials.get("refresh_token", "")
    if not refresh_token:
        raise ValueError("Missing Slack refresh token")

    client_id = getattr(settings, "SLACK_CLIENT_ID", "")
    client_secret = getattr(settings, "SLACK_CLIENT_SECRET", "")
    with httpx.Client(timeout=10) as client:
        response = client.post(
            "https://slack.com/api/oauth.v2.access",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise ValueError("Slack token refresh failed")

    updated = {
        "access_token": payload.get("access_token", ""),
        "refresh_token": payload.get("refresh_token") or refresh_token,
        "expires_in": int(payload.get("expires_in", 0) or 0),
    }

    credentials["access_token"] = updated["access_token"]
    credentials["refresh_token"] = updated["refresh_token"]
    integration.credentials_encrypted = encrypt_credentials(credentials)
    integration.token_expires_at = timezone.now() + timedelta(seconds=updated["expires_in"])
    integration.save(update_fields=["credentials_encrypted", "token_expires_at", "updated_at"])

    return updated


def _ensure_slack_token(integration: Integration) -> str:
    credentials = decrypt_credentials(integration.credentials_encrypted)
    access_token = credentials.get("access_token", "")

    token_expired = (
        integration.token_expires_at is not None
        and integration.token_expires_at <= timezone.now()
    )
    if token_expired:
        refreshed = refresh_slack_access_token(integration)
        return refreshed["access_token"]

    if not access_token:
        raise ValueError("Missing Slack access token")
    return access_token


def _send_slack(integration: Integration, *, event_type: str, payload: dict) -> int:
    access_token = _ensure_slack_token(integration)
    channel_id = integration.config.get("channel_id", "")
    if not channel_id:
        raise ValueError("Slack channel_id is required")

    text = _render_template(
        integration.config.get("message_template", ""),
        event_type=event_type,
        payload=payload,
    )
    with httpx.Client(timeout=10) as client:
        response = client.post(
            "https://slack.com/api/chat.postMessage",
            json={"channel": channel_id, "text": text},
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if response.status_code >= 400:
        raise ValueError(f"Slack delivery failed with {response.status_code}")
    body = response.json()
    if not body.get("ok", False):
        raise ValueError("Slack delivery failed")
    return response.status_code


def _send_teams(integration: Integration, *, event_type: str, payload: dict) -> int:
    credentials = decrypt_credentials(integration.credentials_encrypted)
    webhook_url = credentials.get("webhook_url", "")
    if not webhook_url:
        raise ValueError("Missing Teams webhook_url")

    text = _render_template(
        integration.config.get("message_template", ""),
        event_type=event_type,
        payload=payload,
    )
    with httpx.Client(timeout=10) as client:
        response = client.post(webhook_url, json={"text": text})
    if response.status_code >= 400:
        raise ValueError(f"Teams delivery failed with {response.status_code}")
    return response.status_code


def _send_email(integration: Integration, *, event_type: str, payload: dict) -> int:
    credentials = decrypt_credentials(integration.credentials_encrypted)
    username = credentials.get("smtp_username", "")
    password = credentials.get("smtp_password", "")

    smtp_host = integration.config.get("smtp_host", "")
    smtp_port = int(integration.config.get("smtp_port", 587) or 587)
    from_email = integration.config.get("from_email", "")
    to_email = integration.config.get("to_email", "")
    if not smtp_host or not from_email or not to_email:
        raise ValueError("Email connector smtp_host/from_email/to_email are required")

    body = _render_template(
        integration.config.get("message_template", ""),
        event_type=event_type,
        payload=payload,
    )

    message = EmailMessage()
    message["Subject"] = f"DecisionVault alert: {event_type}"
    message["From"] = from_email
    message["To"] = to_email
    message.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as smtp:
        if username and password:
            smtp.starttls()
            smtp.login(username, password)
        smtp.send_message(message)

    return 250


def send_integration_message(integration: Integration, *, event_type: str, payload: dict) -> int:
    connector_type = integration.connector_type
    if connector_type == Integration.ConnectorType.SLACK:
        return _send_slack(integration, event_type=event_type, payload=payload)
    if connector_type == Integration.ConnectorType.TEAMS:
        return _send_teams(integration, event_type=event_type, payload=payload)
    if connector_type == Integration.ConnectorType.EMAIL:
        return _send_email(integration, event_type=event_type, payload=payload)
    raise ValueError(f"Unsupported connector type: {connector_type}")
