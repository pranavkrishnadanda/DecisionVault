"""OAuth services for third-party connector installation."""

from __future__ import annotations

from urllib.parse import urlencode

import httpx
from django.conf import settings


SLACK_OAUTH_AUTHORIZE_URL = "https://slack.com/oauth/v2/authorize"
SLACK_OAUTH_TOKEN_URL = "https://slack.com/api/oauth.v2.access"


def build_slack_install_url(*, state: str, redirect_uri: str) -> str:
    client_id = getattr(settings, "SLACK_CLIENT_ID", "slack-client-id")
    scopes = getattr(
        settings,
        "SLACK_SCOPES",
        "chat:write,channels:read,channels:join",
    )
    query = urlencode(
        {
            "client_id": client_id,
            "scope": scopes,
            "redirect_uri": redirect_uri,
            "state": state,
        }
    )
    return f"{SLACK_OAUTH_AUTHORIZE_URL}?{query}"


def exchange_slack_oauth_code(*, code: str, redirect_uri: str) -> dict:
    client_id = getattr(settings, "SLACK_CLIENT_ID", "")
    client_secret = getattr(settings, "SLACK_CLIENT_SECRET", "")

    with httpx.Client(timeout=10) as client:
        response = client.post(
            SLACK_OAUTH_TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )

    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise ValueError("Slack OAuth exchange failed")

    return {
        "access_token": payload.get("access_token", ""),
        "refresh_token": payload.get("refresh_token", ""),
        "expires_in": int(payload.get("expires_in", 0) or 0),
    }
