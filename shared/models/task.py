import enum
from datetime import datetime
from sqlalchemy import Enum, DateTime, func, String, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index('ix_tasks_status', 'status'),
        Index('ix_tasks_created_at', 'created_at'),
        Index('ix_tasks_status_created_at', 'status', 'created_at'))

    id: Mapped[int] = mapped_column(primary_key=True)

    payload: Mapped[str] = mapped_column(String, nullable=False)

    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus),
        default=TaskStatus.PENDING,
        nullable=False)
    result: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False)
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False)

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, status={self.status})>"
