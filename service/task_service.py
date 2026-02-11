from typing import Sequence
import logging
from sqlalchemy import select
from shared.models import Task, TaskStatus, Outbox
from shared.schemas import TaskCreate, TaskUpdate

logger = logging.getLogger(__name__)


class TaskService:
    def __init__(self, session):
        self.session = session

    async def create_task(self, task_data: TaskCreate) -> Task:
        """Делаем две записи: в основную бд и outbox"""
        task = Task(payload=task_data.payload, status=TaskStatus.PENDING)
        self.session.add(task)
        await self.session.flush()
        outbox = Outbox(task_id=task.id)
        self.session.add(outbox)
        await self.session.commit()
        logger.info(f"Created task {task.id} with outbox entry")
        return task

    async def get_task(self, task_id: int) -> Task | None:
        result = await self.session.execute(
            select(Task).where(Task.id == task_id))
        return result.scalar_one_or_none()

    async def get_all_tasks(self, skip: int = 0, limit: int = 100) -> Sequence[Task]:
        """Get all tasks with pagination."""
        # Enforce maximum limit to prevent OOM
        result = await self.session.execute(
            select(Task)
            .order_by(Task.created_at.desc())
            .offset(skip)
            .limit(limit))
        return result.scalars().all()

    async def update_task(self, task_id: int, task_data: TaskUpdate) -> Task | None:
        task = await self.get_task(task_id)
        if not task:
            return None
        
        if task_data.payload is not None:
            task.payload = task_data.payload
        if task_data.result is not None:
            task.result = task_data.result
        
        await self.session.commit()
        return task

    async def try_claim_task_for_processing(self, task_id: int) -> tuple[Task | None, str | None]:
        """Try to claim a task for processing with pessimistic lock."""
        result = await self.session.execute(
            select(Task)
            .where(Task.id == task_id)
            .with_for_update())
        task = result.scalar_one_or_none()
        
        if not task or task.status != TaskStatus.PENDING:
            return None, None
        
        task.status = TaskStatus.PROCESSING
        payload = task.payload
        await self.session.commit()
        return task, payload
    
    async def complete_task(self, task_id: int, result_data: str, status: TaskStatus) -> None:
        task = await self.get_task(task_id)
        if task:
            task.status = status
            task.result = result_data
            await self.session.commit()

    async def mark_task_failed(self, task: Task, error: str | None = None) -> None:
        task.status = TaskStatus.FAILED
        if error:
            task.result = f"error: {error}"
        await self.session.commit()

    async def delete_task(self, task_id: int) -> bool:
        result = await self.session.execute(
            select(Task)
            .where(Task.id == task_id)
            .with_for_update())
        task = result.scalar_one_or_none()
        
        if not task:
            return False
        
        if task.status in (TaskStatus.PENDING, TaskStatus.PROCESSING):
            return False
        
        await self.session.delete(task)
        await self.session.commit()
        return True
