from typing import Sequence
import logging
from sqlalchemy import select
from shared.models import Outbox

logger = logging.getLogger(__name__)


class OutboxService:
    
    def __init__(self, session):
        self.session = session
    
    async def get_pending_messages(self, limit: int = 10) -> Sequence[Outbox]:
        result = await self.session.execute(
            select(Outbox).order_by(Outbox.id).limit(limit))
        messages = result.scalars().all()
        logger.debug(f"Retrieved {len(messages)} pending outbox messages")
        return messages
    
    async def delete_message(self, message: Outbox) -> None:
        await self.session.delete(message)
        await self.session.commit()
        logger.debug(f"Deleted outbox message {message.id}")
