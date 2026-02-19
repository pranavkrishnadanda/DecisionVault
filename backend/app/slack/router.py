import hashlib
import hmac
import json
import secrets
from datetime import timedelta
from urllib.parse import urlencode

import httpx
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from api.models import OrganizationMembership
from app.slack.client import SlackClient
from app.slack.encryption import decrypt_token, encrypt_token
from app.slack.models import (
    SlackAuditLog,
    SlackIntegration,
    SlackIntegrationTestLog,
    SlackUserCache,
)


def _member_org(user):
    membership = (
        OrganizationMembership.objects.select_related("organization")
        .filter(user=user)
        .first()
    )
    return membership.organization if membership else None


def _audit(
    action: str, user, details: dict, integration: SlackIntegration | None = None
):
    SlackAuditLog.objects.create(
        integration=integration,
        action=action,
        actor_user=user if user and user.is_authenticated else None,
        details=details,
    )


def _frontend_redirect(status_value: str, reason: str | None = None) -> HttpResponse:
    query = {"status": status_value}
    if reason:
        query["reason"] = reason
    return redirect(f"/integrations/slack?{urlencode(query)}")


def _resolve_integration(
    request: HttpRequest, integration_id: str
) -> SlackIntegration | None:
    integration = (
        SlackIntegration.objects.filter(id=integration_id, is_active=True)
        .select_related("org")
        .first()
    )
    if integration is None:
        return None
    if not OrganizationMembership.objects.filter(
        user=request.user,
        organization_id=integration.org_id,
    ).exists():
        return None
    return integration


@login_required
def install(request: HttpRequest) -> HttpResponse:
    state = secrets.token_urlsafe(32)
    org = _member_org(request.user)
    cache.set(
        f"slack_oauth_state:{state}",
        {
            "user_id": str(request.user.id),
            "org_id": str(org.id) if org else "",
        },
        timeout=600,
    )

    params = {
        "client_id": settings.SLACK_CLIENT_ID,
        "scope": settings.SLACK_SCOPES,
        "redirect_uri": f"{settings.SLACK_REDIRECT_BASE_URL}/api/slack/callback",
        "state": state,
    }
    _audit(SlackAuditLog.Action.INSTALL_INIT, request.user, {"state": state})
    return redirect(f"https://slack.com/oauth/v2/authorize?{urlencode(params)}")


@login_required
def callback(request: HttpRequest) -> HttpResponse:
    code = request.GET.get("code", "")
    state = request.GET.get("state", "")
    state_key = f"slack_oauth_state:{state}"
    state_data = cache.get(state_key)

    if not state or not state_data:
        return _frontend_redirect("error", "invalid_state")

    cache.delete(state_key)

    redirect_uri = f"{settings.SLACK_REDIRECT_BASE_URL}/api/slack/callback"
    oauth_response = httpx.post(
        "https://slack.com/api/oauth.v2.access",
        data={
            "client_id": settings.SLACK_CLIENT_ID,
            "client_secret": settings.SLACK_CLIENT_SECRET,
            "code": code,
            "redirect_uri": redirect_uri,
        },
        timeout=20,
    )
    payload = oauth_response.json()

    if not payload.get("ok"):
        return _frontend_redirect("error", payload.get("error", "oauth_failed"))

    org = _member_org(request.user)
    if org is None:
        return _frontend_redirect("error", "internal")

    token = payload.get("access_token", "")
    if not token:
        return _frontend_redirect("error", "oauth_failed")

    team = payload.get("team") or {}
    integration = SlackIntegration.objects.create(
        org=org,
        team_id=team.get("id", ""),
        team_name=team.get("name", ""),
        encrypted_token=encrypt_token(token),
        bot_user_id=payload.get("bot_user_id", ""),
        installed_by=request.user,
    )
    _audit(
        SlackAuditLog.Action.INSTALL,
        request.user,
        {"team_id": integration.team_id, "team_name": integration.team_name},
        integration=integration,
    )
    return _frontend_redirect("success")


@login_required
def channels(request: HttpRequest) -> HttpResponse:
    integration_id = request.GET.get("integration_id", "")
    integration = _resolve_integration(request, integration_id)
    if integration is None:
        return JsonResponse({"detail": "Forbidden"}, status=403)

    cache_key = f"slack_channels:{integration.id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return JsonResponse(cached, safe=False)

    token = decrypt_token(integration.encrypted_token)
    client = SlackClient(token=token)
    channel_list = client.list_channels()
    cache.set(cache_key, channel_list, timeout=60)

    _audit(
        SlackAuditLog.Action.CHANNEL_LIST,
        request.user,
        {"count": len(channel_list)},
        integration=integration,
    )
    return JsonResponse(channel_list, safe=False)


@login_required
def integrations(request: HttpRequest) -> HttpResponse:
    org = _member_org(request.user)
    if org is None:
        return JsonResponse([], safe=False)

    rows = SlackIntegration.objects.filter(org=org, is_active=True).order_by(
        "-installed_at"
    )
    payload = [
        {
            "id": str(item.id),
            "team_id": item.team_id,
            "team_name": item.team_name,
            "installed_at": item.installed_at.isoformat(),
        }
        for item in rows
    ]
    return JsonResponse(payload, safe=False)


@login_required
def messages(request: HttpRequest) -> HttpResponse:
    integration_id = request.GET.get("integration_id", "")
    channel_id = request.GET.get("channel_id", "")
    oldest = request.GET.get("oldest", "")
    limit = int(request.GET.get("limit", "100"))

    integration = _resolve_integration(request, integration_id)
    if integration is None:
        return JsonResponse({"detail": "Forbidden"}, status=403)

    token = decrypt_token(integration.encrypted_token)
    client = SlackClient(token=token)
    history = client.get_messages(channel_id=channel_id, oldest=oldest, limit=limit)

    response_messages: list[dict] = []
    one_hour_ago = timezone.now() - timedelta(hours=1)

    for item in history.get("messages", []):
        user_id = item.get("user", "")
        user_name = "Unknown"

        if user_id:
            cached_user = SlackUserCache.objects.filter(
                integration=integration,
                slack_user_id=user_id,
                cached_at__gte=one_hour_ago,
            ).first()
            if cached_user:
                user_name = cached_user.display_name or cached_user.real_name or user_id
            else:
                profile = client.get_user(user_id)
                user_name = profile.get("display_name") or user_id
                SlackUserCache.objects.update_or_create(
                    integration=integration,
                    slack_user_id=user_id,
                    defaults={
                        "display_name": profile.get("display_name", ""),
                        "real_name": profile.get("real_name", ""),
                        "avatar_url": profile.get("avatar_url", ""),
                        "cached_at": timezone.now(),
                    },
                )

        replies_payload = []
        if item.get("thread_ts"):
            replies = client.get_replies(
                channel_id=channel_id, thread_ts=item["thread_ts"]
            )
            for reply in replies:
                reply_user_id = reply.get("user", "")
                reply_user_name = reply_user_id
                if reply_user_id:
                    profile = client.get_user(reply_user_id)
                    reply_user_name = profile.get("display_name") or reply_user_id
                replies_payload.append(
                    {
                        "user_name": reply_user_name,
                        "text": reply.get("text", ""),
                        "ts": reply.get("ts", ""),
                    }
                )

        response_messages.append(
            {
                "user_name": user_name,
                "text": item.get("text", ""),
                "ts": item.get("ts", ""),
                "thread_replies": replies_payload,
            }
        )

    payload = {
        "messages": response_messages,
        "has_more": history.get("has_more", False),
        "next_cursor": history.get("next_cursor", ""),
    }
    _audit(
        SlackAuditLog.Action.MESSAGE_FETCH,
        request.user,
        {"channel_id": channel_id, "count": len(response_messages)},
        integration=integration,
    )
    return JsonResponse(payload)


@login_required
@csrf_exempt
def send_test(request: HttpRequest) -> HttpResponse:
    payload = json.loads(request.body or b"{}")
    integration_id = payload.get("integration_id", "")
    channel_id = payload.get("channel_id", "")

    integration = _resolve_integration(request, integration_id)
    if integration is None:
        return JsonResponse({"detail": "Forbidden"}, status=403)

    token = decrypt_token(integration.encrypted_token)
    client = SlackClient(token=token)
    result = client.send_message(
        channel_id=channel_id,
        text="✓ Integration test from DecisionVault",
    )

    success = bool(result.get("ok", False))
    error = result.get("error", "") if not success else ""
    message_ts = result.get("ts", "") if success else ""

    SlackIntegrationTestLog.objects.create(
        integration=integration,
        channel_id=channel_id,
        success=success,
        error=error,
        message_ts=message_ts,
    )
    _audit(
        SlackAuditLog.Action.TEST_SEND,
        request.user,
        {"channel_id": channel_id, "success": success, "error": error},
        integration=integration,
    )

    return JsonResponse(
        {
            "success": success,
            "error": error or None,
            "message_ts": message_ts or None,
        }
    )


def _verify_slack_signature(request: HttpRequest) -> bool:
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")
    if not timestamp or not signature:
        return False

    body = request.body.decode("utf-8")
    basestring = f"v0:{timestamp}:{body}".encode("utf-8")
    expected = (
        "v0="
        + hmac.new(
            settings.SLACK_SIGNING_SECRET.encode("utf-8"),
            basestring,
            hashlib.sha256,
        ).hexdigest()
    )
    return hmac.compare_digest(expected, signature)


@csrf_exempt
def events(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    if not _verify_slack_signature(request):
        return JsonResponse({"detail": "Invalid signature"}, status=401)

    payload = json.loads(request.body or b"{}")
    _audit(
        SlackAuditLog.Action.EVENT_RECEIVED,
        request.user if hasattr(request, "user") else None,
        {"type": payload.get("type", "unknown")},
        integration=None,
    )

    if payload.get("type") == "url_verification":
        return JsonResponse({"challenge": payload.get("challenge", "")})

    return JsonResponse({"ok": True})
