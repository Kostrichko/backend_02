import asyncio
import logging
import aio_pika
from aio_pika import Message, DeliveryMode
from shared.config import settings
import json

logger = logging.getLogger(__name__)


class Queue:
    def __init__(self):
        self.connection = None
        self.channel = None

    async def connect(self):
        logger.info(f"Connecting to RabbitMQ at {settings.RABBITMQ_URL}")
        self.connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        self.channel = await self.connection.channel()
        await self.channel.declare_queue(settings.RABBITMQ_QUEUE, durable=True)
        logger.info(f"Connected to queue '{settings.RABBITMQ_QUEUE}'")

    async def disconnect(self):
        if self.connection:
            await self.connection.close()
            logger.info("Disconnected from RabbitMQ")

    async def publish(self, message: dict):
        await self.channel.default_exchange.publish(
            Message(
                body=json.dumps(message).encode(),
                delivery_mode=DeliveryMode.PERSISTENT,
            ),
            routing_key=settings.RABBITMQ_QUEUE,
        )

    async def consume(self, callback):
        await self.channel.set_qos(prefetch_count=1)
        queue = await self.channel.declare_queue(settings.RABBITMQ_QUEUE, durable=True)
        await queue.consume(callback)
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            return


queue = Queue()
