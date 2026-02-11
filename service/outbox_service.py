from typing import Sequence
from sqlalchemy import select
from shared.models import Outbox


class OutboxService:
    """Service for managing outbox pattern messages."""
    
    def __init__(self, session):
        self.session = session
    
    async def get_pending_messages(self, limit: int = 10) -> Sequence[Outbox]:
        """Get pending outbox messages ordered by ID."""
        result = await self.session.execute(
            select(Outbox).order_by(Outbox.id).limit(limit)
        )
        return result.scalars().all()
    
    async def delete_message(self, message: Outbox) -> None:
        """Delete a message from outbox."""
        await self.session.delete(message)
        await self.session.commit()
