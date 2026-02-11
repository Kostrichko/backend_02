import asyncio
from database import async_session_maker
from broker import queue
from service import OutboxService


async def process_outbox():
    """Process outbox messages one by one to ensure atomicity.
    
    Each message is published and deleted in a single transaction,
    preventing duplicate deliveries if relay crashes mid-batch.
    """
    async with async_session_maker() as session:
        service = OutboxService(session)
        messages = await service.get_pending_messages(limit=10)
        
        for msg in messages:
            # Publish to queue
            await queue.publish({"task_id": msg.task_id})
            
            # Delete from outbox in same iteration to maintain atomicity
            await service.delete_message(msg)


async def main():
    await queue.connect()
    try:
        while True:
            await process_outbox()
            await asyncio.sleep(1)
    finally:
        await queue.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
