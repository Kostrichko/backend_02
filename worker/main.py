import json
from aio_pika.abc import AbstractIncomingMessage
from database import async_session_maker
from broker import queue
from service import TaskService
from shared.models import TaskStatus
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
            service = TaskService(session)
            
            # Try to claim task with pessimistic lock
            task, payload = await service.try_claim_task_for_processing(task_id)
            if not task:
                return
            
            # Process work
            try:
                result_data = await work(payload)
                new_status = TaskStatus.DONE
            except Exception as e:
                result_data = str(e)
                new_status = TaskStatus.FAILED
            
            # Update task with result
            await service.complete_task(task_id, result_data, new_status)


async def main():
    await queue.connect()
    try:
        await queue.consume(message_consume)
    finally:
        await queue.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
