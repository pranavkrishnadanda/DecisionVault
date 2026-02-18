"""Tests for RabbitMQ decision worker consumer using TDD."""

import json
from unittest.mock import MagicMock, patch

import pika
import pytest
from django.conf import settings

from core.constants import DECISION_TASKS_QUEUE
from decisions.models import Decision, DecisionStatus
from workers.consumers import TaskConsumer
from workers.tasks import process_decision_task


class TestTaskConsumerUnit:
    @patch("workers.consumers.pika.BlockingConnection")
    def test_connect_declares_canonical_queue_and_sets_qos(self, mock_connection_cls):
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_connection.channel.return_value = mock_channel
        mock_connection_cls.return_value = mock_connection

        consumer = TaskConsumer(task_handlers={"decision.process": MagicMock()})
        consumer.connect(host="localhost", port=5672)

        mock_channel.queue_declare.assert_called_once_with(
            queue=DECISION_TASKS_QUEUE,
            durable=True,
        )
        mock_channel.basic_qos.assert_called_once_with(prefetch_count=1)

    def test_on_message_acks_when_handler_succeeds(self):
        handler = MagicMock()
        consumer = TaskConsumer(task_handlers={"decision.process": handler})

        channel = MagicMock()
        method = MagicMock()
        method.delivery_tag = "tag-1"

        body = json.dumps({"type": "decision.process", "payload": {"decision_id": "123"}}).encode()

        consumer._on_message(channel, method, None, body)

        handler.assert_called_once()
        channel.basic_ack.assert_called_once_with("tag-1")

    def test_on_message_nacks_unknown_task_without_requeue(self):
        consumer = TaskConsumer(task_handlers={})
        channel = MagicMock()
        method = MagicMock()
        method.delivery_tag = "tag-2"

        body = json.dumps({"type": "unknown.task", "payload": {}}).encode()

        consumer._on_message(channel, method, None, body)

        channel.basic_nack.assert_called_once_with("tag-2", requeue=False)

    def test_on_message_nacks_invalid_json_without_requeue(self):
        consumer = TaskConsumer(task_handlers={"decision.process": MagicMock()})
        channel = MagicMock()
        method = MagicMock()
        method.delivery_tag = "tag-3"

        consumer._on_message(channel, method, None, b"not-json")

        channel.basic_nack.assert_called_once_with("tag-3", requeue=False)

    def test_on_message_nacks_with_requeue_on_handler_exception(self):
        handler = MagicMock(side_effect=RuntimeError("boom"))
        consumer = TaskConsumer(task_handlers={"decision.process": handler})

        channel = MagicMock()
        method = MagicMock()
        method.delivery_tag = "tag-4"
        body = json.dumps({"type": "decision.process", "payload": {"decision_id": "123"}}).encode()

        consumer._on_message(channel, method, None, body)

        channel.basic_nack.assert_called_once_with("tag-4", requeue=True)


@pytest.mark.django_db
class TestTaskConsumerIntegration:
    @pytest.fixture(autouse=True)
    def purge_queue(self):
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
            )
        )
        channel = connection.channel()
        channel.queue_declare(queue=DECISION_TASKS_QUEUE, durable=True)
        channel.queue_purge(queue=DECISION_TASKS_QUEUE)
        connection.close()

        yield

        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
            )
        )
        channel = connection.channel()
        channel.queue_purge(queue=DECISION_TASKS_QUEUE)
        connection.close()

    def test_consume_once_processes_decision_message(self):
        decision = Decision.objects.create(
            title="Integration Decision",
            description="Process from queue",
            created_by="user_1",
            status=DecisionStatus.PENDING,
            metadata={"source": "queue"},
        )

        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
            )
        )
        channel = connection.channel()
        channel.basic_publish(
            exchange="",
            routing_key=DECISION_TASKS_QUEUE,
            body=json.dumps({
                "type": "decision.process",
                "payload": {"decision_id": str(decision.id)},
            }),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        connection.close()

        consumer = TaskConsumer(task_handlers={"decision.process": process_decision_task})
        consumer.connect(host=settings.RABBITMQ_HOST, port=settings.RABBITMQ_PORT)

        consumed = consumer.consume_once()
        consumer.close()

        assert consumed is True

        decision.refresh_from_db()
        assert decision.status in {DecisionStatus.COMPLETED, DecisionStatus.FAILED}
        assert decision.workflow_completed_at is not None
