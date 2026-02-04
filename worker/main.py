import json
from aio_pika.abc import AbstractIncomingMessage
from database import async_session_maker
from broker import queue
from shared.models import Task, TaskStatus
from worker.solver import work
import asyncio

async def message_consume(message: AbstractIncomingMessage):
    async with message.process():
        try:
            data = json.loads(message.body.decode())
            task_id = data["task_id"]
        except Exception:
            return

        async with async_session_maker() as session:
            db_task = await session.get(Task, task_id)
            
            if not db_task or db_task.status != TaskStatus.PENDING:
                return

            db_task.status = TaskStatus.PROCESSING
            payload = db_task.payload
            await session.commit()

        try:
            result_data = await work(payload)
            new_status = TaskStatus.DONE
        except Exception as e:
            result_data = str(e)
            new_status = TaskStatus.FAILED

        async with async_session_maker() as session:
            db_task = await session.get(Task, task_id)
            if db_task:
                db_task.status = new_status
                db_task.result = result_data
                await session.commit()


async def main():
    await queue.connect()
    try:
        await queue.consume(message_consume)
    finally:
        await queue.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
