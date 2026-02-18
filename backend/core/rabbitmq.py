import os
import pika
import json


class RabbitMQClient:
    """
    RabbitMQ client for publishing messages to the decision_tasks queue.
    
    Usage:
        client = RabbitMQClient()
        client.publish({"task": "process", "data": {...}})
        client.close()
    """
    
    def __init__(self, host=None, port=None):
        """
        Initialize RabbitMQ connection.
        
        Args:
            host: RabbitMQ host (defaults to RABBITMQ_HOST env var)
            port: RabbitMQ port (defaults to RABBITMQ_PORT env var)
        """
        self.host = host or os.getenv("RABBITMQ_HOST", "localhost")
        self.port = port or int(os.getenv("RABBITMQ_PORT", "5672"))
        
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.host,
                port=self.port,
            )
        )
        self.channel = self.connection.channel()

        self.channel.queue_declare(
            queue="decision_tasks",
            durable=True,
        )

    def publish(self, data: dict):
        """
        Publish a message to the decision_tasks queue.
        
        Args:
            data: Dictionary to be JSON-serialized and published.
        """
        self.channel.basic_publish(
            exchange="",
            routing_key="decision_tasks",
            body=json.dumps(data),
            properties=pika.BasicProperties(
                delivery_mode=2,  # persistent
            ),
        )

    def close(self):
        """Close the RabbitMQ connection."""
        self.connection.close()