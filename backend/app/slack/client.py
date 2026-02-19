import logging
import time
from typing import Any

import httpx


logger = logging.getLogger(__name__)


class SlackClient:
    def __init__(
        self,
        token: str,
        base_url: str = "https://slack.com/api",
        timeout: float = 15.0,
        transport: httpx.BaseTransport | None = None,
        max_retries: int = 4,
    ) -> None:
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = httpx.Client(timeout=timeout, transport=transport)

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.token}"
        headers["Content-Type"] = "application/x-www-form-urlencoded"

        attempt = 0
        while True:
            started = time.monotonic()
            response = self.client.request(
                method,
                f"{self.base_url}/{endpoint}",
                headers=headers,
                **kwargs,
            )
            duration_ms = int((time.monotonic() - started) * 1000)

            if response.status_code == 429 and attempt < self.max_retries:
                retry_after = int(response.headers.get("Retry-After", "1"))
                logger.warning(
                    "Slack API rate-limited",
                    extra={
                        "endpoint": endpoint,
                        "status_code": 429,
                        "attempt": attempt,
                        "duration_ms": duration_ms,
                    },
                )
                time.sleep(min(max(retry_after, 1), 60))
                attempt += 1
                continue

            payload = response.json()
            logger.info(
                "Slack API call",
                extra={
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "attempt": attempt,
                    "ok": bool(payload.get("ok", False)),
                    "duration_ms": duration_ms,
                },
            )
            return payload

    def list_channels(self, cursor: str = "") -> list[dict[str, Any]]:
        payload = self._request(
            "GET",
            "conversations.list",
            params={
                "types": "public_channel,private_channel",
                "limit": 200,
                "cursor": cursor,
            },
        )
        channels = payload.get("channels")
        if not isinstance(channels, list):
            return []
        return [
            {
                "id": item.get("id", ""),
                "name": item.get("name", ""),
                "is_private": bool(item.get("is_private", False)),
                "num_members": item.get("num_members", 0),
                "topic": (item.get("topic") or {}).get("value", ""),
            }
            for item in channels
        ]

    def get_messages(self, channel_id: str, oldest: str = "", limit: int = 100) -> dict[str, Any]:
        payload = self._request(
            "GET",
            "conversations.history",
            params={
                "channel": channel_id,
                "oldest": oldest,
                "limit": min(max(limit, 1), 200),
            },
        )
        metadata = payload.get("response_metadata") or {}
        return {
            "messages": payload.get("messages", []),
            "has_more": bool(payload.get("has_more", False)),
            "next_cursor": metadata.get("next_cursor", ""),
        }

    def get_replies(self, channel_id: str, thread_ts: str) -> list[dict[str, Any]]:
        payload = self._request(
            "GET",
            "conversations.replies",
            params={"channel": channel_id, "ts": thread_ts, "limit": 200},
        )
        messages = payload.get("messages")
        if not isinstance(messages, list):
            return []
        return [m for m in messages if m.get("ts") != thread_ts]

    def send_message(self, channel_id: str, text: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "chat.postMessage",
            data={"channel": channel_id, "text": text},
        )

    def get_user(self, user_id: str) -> dict[str, Any]:
        payload = self._request(
            "GET",
            "users.info",
            params={"user": user_id},
        )
        profile = ((payload.get("user") or {}).get("profile") or {})
        return {
            "display_name": profile.get("display_name") or profile.get("real_name") or user_id,
            "real_name": profile.get("real_name", ""),
            "avatar_url": profile.get("image_72", ""),
        }
