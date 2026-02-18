from core.rabbitmq import RabbitMQClient

mq = RabbitMQClient()

mq.publish({"type": "test", "message": "Hello from Django"})

mq.close()

print("Sent!")
