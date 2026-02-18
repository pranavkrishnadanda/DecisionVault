"""
Integration tests for RabbitMQ connectivity.

These tests verify that RabbitMQ is properly configured and accessible.
They require RabbitMQ to be running on the configured host/port.

Run with: pytest tests/test_rabbitmq_integration.py -v
"""

import os
import json
import pytest
import pika
from django.conf import settings

from core.rabbitmq import RabbitMQClient


class TestRabbitMQSettings:
    """Test RabbitMQ settings configuration."""

    def test_rabbitmq_host_configured(self):
        """
        RabbitMQ host must be configured.
        """
        assert hasattr(settings, "RABBITMQ_HOST")
        assert settings.RABBITMQ_HOST is not None

    def test_rabbitmq_port_configured(self):
        """
        RabbitMQ port must be configured as integer.
        """
        assert hasattr(settings, "RABBITMQ_PORT")
        assert isinstance(settings.RABBITMQ_PORT, int)
        assert settings.RABBITMQ_PORT > 0


class TestRabbitMQConnection:
    """Test RabbitMQ connectivity."""

    def test_rabbitmq_connection_establishes(self):
        """
        Should be able to establish connection to RabbitMQ.
        
        This test will fail if RabbitMQ is not running.
        """
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=settings.RABBITMQ_HOST,
                    port=settings.RABBITMQ_PORT,
                )
            )
            assert connection.is_open
            connection.close()
        except pika.exceptions.AMQPConnectionError as e:
            pytest.fail(f"RabbitMQ connection failed: {e}")

    def test_rabbitmq_channel_opens(self):
        """
        Should be able to open a channel.
        """
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=settings.RABBITMQ_HOST,
                    port=settings.RABBITMQ_PORT,
                )
            )
            channel = connection.channel()
            assert channel.is_open
            channel.close()
            connection.close()
        except pika.exceptions.AMQPConnectionError as e:
            pytest.fail(f"RabbitMQ channel failed: {e}")

    def test_rabbitmq_queue_declares(self):
        """
        Should be able to declare the decision_tasks queue.
        """
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=settings.RABBITMQ_HOST,
                    port=settings.RABBITMQ_PORT,
                )
            )
            channel = connection.channel()
            
            # Declare queue (idempotent if already exists)
            channel.queue_declare(
                queue="decision_tasks",
                durable=True,
            )
            
            # Verify queue exists
            method_frame = channel.queue_declare(
                queue="decision_tasks",
                passive=True,
            )
            assert method_frame.method.queue == "decision_tasks"
            
            channel.close()
            connection.close()
        except pika.exceptions.AMQPConnectionError as e:
            pytest.fail(f"RabbitMQ queue declaration failed: {e}")


class TestRabbitMQClient:
    """Test the RabbitMQClient wrapper class."""

    @pytest.fixture
    def rabbitmq_client(self):
        """Create a RabbitMQClient instance."""
        client = RabbitMQClient()
        yield client
        client.close()

    @pytest.fixture(autouse=True)
    def purge_queue(self, rabbitmq_client):
        """Purge queue before and after each test."""
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
            )
        )
        channel = connection.channel()
        channel.queue_purge(queue="decision_tasks")
        connection.close()
        yield
        # Cleanup after test
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
            )
        )
        channel = connection.channel()
        channel.queue_purge(queue="decision_tasks")
        connection.close()

    def test_client_uses_env_settings(self):
        """
        RabbitMQClient should use environment variables by default.
        """
        client = RabbitMQClient()
        assert client.host == settings.RABBITMQ_HOST
        assert client.port == settings.RABBITMQ_PORT
        client.close()

    def test_client_publishes_message(self, rabbitmq_client):
        """
        Client should publish messages to the queue.
        """
        test_data = {"task": "test_task", "payload": {"id": 123}}
        
        # Publish message
        rabbitmq_client.publish(test_data)
        
        # Verify message is in queue by consuming it
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
            )
        )
        channel = connection.channel()
        
        method_frame, properties, body = channel.basic_get(
            queue="decision_tasks",
            auto_ack=True,
        )
        
        assert method_frame is not None, "No message found in queue"
        received_data = json.loads(body)
        assert received_data == test_data
        
        connection.close()

    def test_client_publishes_multiple_messages(self, rabbitmq_client):
        """
        Client should handle multiple message publishes.
        """
        messages = [
            {"task": "task_1", "data": "first"},
            {"task": "task_2", "data": "second"},
            {"task": "task_3", "data": "third"},
        ]
        
        for msg in messages:
            rabbitmq_client.publish(msg)
        
        # Verify all messages are in queue
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
            )
        )
        channel = connection.channel()
        
        received = []
        for _ in range(3):
            method_frame, properties, body = channel.basic_get(
                queue="decision_tasks",
                auto_ack=True,
            )
            if method_frame:
                received.append(json.loads(body))
        
        connection.close()
        
        assert len(received) == 3
        assert received[0]["task"] == "task_1"
        assert received[1]["task"] == "task_2"
        assert received[2]["task"] == "task_3"
