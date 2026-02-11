from datetime import datetime
from sqlalchemy import DateTime, func, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from shared.models.task import Base


class Outbox(Base):
    __tablename__ = "outbox"
    __table_args__ = (
        Index('ix_outbox_task_id', 'task_id'),
        Index('ix_outbox_created_at', 'created_at'))

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey('tasks.id', ondelete='CASCADE'),
        nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now())
