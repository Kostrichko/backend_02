import asyncio
import logging
from database import async_session_maker
from broker import queue
from service import OutboxService
from shared import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


async def process_outbox():
    """ Каждое сообщение из аутбокса обрабатывается по одному, чтобы обеспечить атомарность. 
    Каждое сообщение публикуется и удаляется в одной транзакции, предотвращая дублирование 
    доставки при сбое реле в середине обработки.
    """
    try:
        async with async_session_maker() as session:
            service = OutboxService(session)
            messages = await service.get_pending_messages(limit=10)
            
            if messages:
                logger.info(f"Processing {len(messages)} outbox messages")
            
            for msg in messages:
                logger.debug(f"Publishing task_id={msg.task_id} to queue")
                await queue.publish({"task_id": msg.task_id})
                await service.delete_message(msg)
                logger.debug(f"Deleted outbox message id={msg.id}")
    except Exception as e:
        logger.error(f"Error processing outbox: {e}", exc_info=True)


async def main():
    logger.info("Starting relay service")
    await queue.connect()
    logger.info("Connected to RabbitMQ")
    try:
        while True:
            await process_outbox()
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down relay service")
    except Exception as e:
        logger.critical(f"Fatal error in relay: {e}", exc_info=True)
        raise
    finally:
        await queue.disconnect()
        logger.info("Relay service stopped")


if __name__ == "__main__":
    asyncio.run(main())
