import httpx
from unittest.mock import patch

from app.slack.client import SlackClient


def test_rate_limit_backoff_retries_and_succeeds():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "2"}, json={"ok": False})
        return httpx.Response(200, json={"ok": True, "channels": []})

    transport = httpx.MockTransport(handler)

    with patch("time.sleep") as sleep_mock:
        client = SlackClient(token="xoxb-token", transport=transport, max_retries=2)
        response = client.list_channels()

    assert response == []
    sleep_mock.assert_called_once_with(2)
    assert calls["n"] == 2
