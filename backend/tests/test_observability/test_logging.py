"""Observability logging tests for Phase 3.0."""

import json
import logging

import pytest

from decisions.services import RabbitMQService


def test_json_formatter_emits_structured_fields():
    from core.observability import JsonFormatter

    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="decisionvault.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=12,
        msg="test message",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-123"
    record.correlation_id = "corr-456"
    record.decision_id = "dec-789"

    payload = json.loads(formatter.format(record))

    assert payload["message"] == "test message"
    assert payload["level"] == "INFO"
    assert payload["request_id"] == "req-123"
    assert payload["correlation_id"] == "corr-456"
    assert payload["decision_id"] == "dec-789"
    assert "timestamp" in payload


@pytest.mark.django_db
def test_publish_logs_trace_context(caplog):
    service = RabbitMQService()
    published = {}

    class DummyChannel:
        is_closed = False

        def basic_publish(self, exchange, routing_key, body, properties):
            published["routing_key"] = routing_key

    service._channel = DummyChannel()

    with caplog.at_level(logging.INFO):
        ok = service.publish("11111111-1111-1111-1111-111111111111")

    assert ok is True
    assert published["routing_key"] == service.QUEUE_NAME

    publish_records = [
        record
        for record in caplog.records
        if record.getMessage() == "Published decision task message"
    ]
    assert publish_records
    record = publish_records[0]
    assert record.queue == service.QUEUE_NAME
    assert record.decision_id == "11111111-1111-1111-1111-111111111111"
    assert record.correlation_id == "decision_11111111-1111-1111-1111-111111111111"
