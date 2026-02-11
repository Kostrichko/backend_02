import json
import logging
from aio_pika.abc import AbstractIncomingMessage
from database import async_session_maker
from broker import queue
from service import TaskService
from shared.models import TaskStatus
from shared import setup_logging
from worker.solver import work
import asyncio

setup_logging()
logger = logging.getLogger(__name__)

async def message_consume(message: AbstractIncomingMessage):
    async with message.process():
        try:
            data = json.loads(message.body.decode())
            task_id = data["task_id"]
            logger.info(f"Received message for task_id={task_id}")
        except Exception as e:
            logger.warning(f"Failed to parse message: {e}")
            return

        try:
            async with async_session_maker() as session:
                service = TaskService(session)
                
                # Try to claim task with pessimistic lock
                task, payload = await service.try_claim_task_for_processing(task_id)
                if not task:
                    logger.info(f"Task {task_id} already processed or not found")
                    return
                
                logger.info(f"Processing task {task_id}")
                
                # Process work
                try:
                    result_data = await work(payload)
                    new_status = TaskStatus.DONE
                    logger.info(f"Task {task_id} completed successfully")
                except Exception as e:
                    result_data = str(e)
                    new_status = TaskStatus.FAILED
                    logger.error(f"Task {task_id} failed: {e}")
                
                # Update task with result
                await service.complete_task(task_id, result_data, new_status)
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}", exc_info=True)


async def main():
    logger.info("Starting worker service")
    await queue.connect()
    logger.info("Connected to RabbitMQ, waiting for messages")
    try:
        await queue.consume(message_consume)
    except KeyboardInterrupt:
        logger.info("Shutting down worker service")
    except Exception as e:
        logger.critical(f"Fatal error in worker: {e}", exc_info=True)
        raise
    finally:
        await queue.disconnect()
        logger.info("Worker service stopped")


if __name__ == "__main__":
    asyncio.run(main())
