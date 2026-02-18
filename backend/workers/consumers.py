"""RabbitMQ consumer implementation for DecisionVault workers."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

import pika

from core.constants import DECISION_TASKS_QUEUE

logger = logging.getLogger(__name__)


class TaskConsumer:
    """RabbitMQ consumer for processing async tasks."""

    QUEUE_NAME = DECISION_TASKS_QUEUE
    PREFETCH_COUNT = 1

    def __init__(self, task_handlers: dict[str, Callable[[dict[str, Any]], Any]]):
        self.task_handlers = task_handlers
        self.connection: pika.BlockingConnection | None = None
        self.channel: pika.adapters.blocking_connection.BlockingChannel | None = None

    def connect(self, host: str = "localhost", port: int = 5672) -> None:
        """Establish RabbitMQ connection and channel QoS."""
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=host,
                port=port,
                heartbeat=600,
            )
        )
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.QUEUE_NAME, durable=True)
        self.channel.basic_qos(prefetch_count=self.PREFETCH_COUNT)

    def start_consuming(self) -> None:
        """Start continuous message consumption."""
        if self.channel is None:
            raise RuntimeError("Consumer must be connected before start_consuming")

        self.channel.basic_consume(
            queue=self.QUEUE_NAME,
            on_message_callback=self._on_message,
        )
        logger.info("Starting consumer on queue: %s", self.QUEUE_NAME)
        self.channel.start_consuming()

    def consume_once(self) -> bool:
        """Consume and process at most one message. Returns True when a message was processed."""
        if self.channel is None:
            raise RuntimeError("Consumer must be connected before consume_once")

        method_frame, properties, body = self.channel.basic_get(
            queue=self.QUEUE_NAME,
            auto_ack=False,
        )
        if method_frame is None:
            return False

        self._on_message(self.channel, method_frame, properties, body)
        return True

    def _on_message(
        self,
        channel: pika.adapters.blocking_connection.BlockingChannel,
        method: pika.spec.Basic.Deliver,
        properties: pika.BasicProperties | None,
        body: bytes,
    ) -> None:
        """Handle incoming RabbitMQ message."""
        try:
            message = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            logger.exception("Malformed worker message; dropping")
            channel.basic_nack(method.delivery_tag, requeue=False)
            return

        task_type = message.get("type") or message.get("task_type")
        if task_type not in self.task_handlers:
            logger.error("Unknown task type: %s", task_type)
            channel.basic_nack(method.delivery_tag, requeue=False)
            return

        try:
            handler = self.task_handlers[task_type]
            handler(message)
            channel.basic_ack(method.delivery_tag)
            logger.info("Task completed: %s", task_type)
        except Exception:
            logger.exception("Task processing failed for task type: %s", task_type)
            channel.basic_nack(method.delivery_tag, requeue=True)

    def close(self) -> None:
        """Close channel and connection if open."""
        if self.channel is not None and getattr(self.channel, "is_open", False):
            self.channel.close()
        if self.connection is not None and self.connection.is_open:
            self.connection.close()
