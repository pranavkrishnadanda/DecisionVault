"""Webhook signing primitives and replay-window helpers."""

import hmac
import json
from datetime import timedelta
from datetime import timezone as dt_timezone
from hashlib import sha256

from django.utils import timezone

SIGNATURE_HEADER = "X-DecisionVault-Signature"
TIMESTAMP_HEADER = "X-DecisionVault-Timestamp"

REPLAY_WINDOW = timedelta(minutes=5)


def serialize_payload(payload: dict) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def sign_payload(payload: dict, secret: str, timestamp: str) -> str:
    payload_str = serialize_payload(payload)
    signed = f"{timestamp}.{payload_str}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), signed, sha256).hexdigest()
    return f"sha256={digest}"


def build_signature_headers(payload: dict, secret: str) -> dict[str, str]:
    timestamp = str(int(timezone.now().timestamp()))
    signature = sign_payload(payload=payload, secret=secret, timestamp=timestamp)
    return {
        TIMESTAMP_HEADER: timestamp,
        SIGNATURE_HEADER: signature,
    }


def is_timestamp_within_window(timestamp: str, now=None) -> bool:
    current = now or timezone.now()
    try:
        ts_int = int(timestamp)
    except (TypeError, ValueError):
        return False

    ts_dt = timezone.datetime.fromtimestamp(ts_int, tz=dt_timezone.utc)
    delta = abs(current - ts_dt)
    return delta <= REPLAY_WINDOW
