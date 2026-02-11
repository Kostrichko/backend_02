import asyncio
from sqlalchemy import select, delete
from database import async_session_maker
from broker import queue
from shared.models import Outbox


async def process_outbox():
    async with async_session_maker() as session:
        result = await session.execute(
            select(Outbox).order_by(Outbox.id).limit(10)
        )
        messages = result.scalars().all()
        if not messages:
            return
        for msg in messages:
            await queue.publish({"task_id": msg.task_id})
        msg_ids = [msg.id for msg in messages]
        await session.execute(delete(Outbox).where(Outbox.id.in_(msg_ids)))
        await session.commit()


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
