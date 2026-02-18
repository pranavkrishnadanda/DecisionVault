"""Realtime decision event broker for SSE streams."""

from __future__ import annotations

import json
from queue import Empty, Queue
from threading import Lock
from typing import Callable


class DecisionEventBroker:
    """In-process pub/sub for decision SSE events."""

    def __init__(self):
        self._lock = Lock()
        self._subscribers: set[Queue[str]] = set()

    def subscribe(self) -> tuple[Queue[str], Callable[[], None]]:
        queue: Queue[str] = Queue()

        with self._lock:
            self._subscribers.add(queue)

        def unsubscribe() -> None:
            with self._lock:
                self._subscribers.discard(queue)

        return queue, unsubscribe

    def publish(self, event_name: str, payload: dict) -> None:
        message = self._format_sse(event_name=event_name, payload=payload)
        with self._lock:
            subscribers = list(self._subscribers)

        for subscriber in subscribers:
            subscriber.put(message)

    @staticmethod
    def _format_sse(event_name: str, payload: dict) -> str:
        data = json.dumps(payload)
        return f"event: {event_name}\\ndata: {data}\\n\\n"


decision_event_broker = DecisionEventBroker()


def event_stream_generator(queue: Queue[str]):
    """Yield SSE events with keepalive comments."""
    yield ": connected\\n\\n"

    while True:
        try:
            message = queue.get(timeout=15)
            yield message
        except Empty:
            yield ": keepalive\\n\\n"
