import asyncio
import aio_pika
from aio_pika import Message, DeliveryMode
from shared.config import settings


class Queue:
    def __init__(self):
        self.connection = None
        self.channel = None

    async def connect(self):
        self.connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        self.channel = await self.connection.channel()
        await self.channel.declare_queue(settings.RABBITMQ_QUEUE, durable=True)

    async def disconnect(self):
        if self.connection:
            await self.connection.close()

    async def publish(self, message):
        await self.channel.default_exchange.publish(
            Message(
                body=message.to_json().encode(),
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
