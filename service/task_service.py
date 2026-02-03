from typing import Sequence
from sqlalchemy import select
from shared.models import Task, TaskStatus, Outbox
from shared.schemas import TaskCreate, TaskUpdate


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
        return task

    async def get_task(self, task_id: int) -> Task | None:
        result = await self.session.execute(
            select(Task).where(Task.id == task_id)
        )
        return result.scalar_one_or_none()

    async def get_all_tasks(self) -> Sequence[Task]:
        result = await self.session.execute(select(Task))
        return result.scalars().all()

    async def update_task(self, task_id: int, task_data: TaskUpdate) -> Task | None:
        """Заглушка"""
        return await self.get_task(task_id)

    async def mark_task_failed(self, task: Task, error: str | None = None) -> None:
        task.status = TaskStatus.FAILED
        if error:
            task.result = f"error: {error}"
        await self.session.commit()

    async def delete_task(self, task_id: int) -> bool:
        task = await self.get_task(task_id)
        if not task:
            return False
        """Не лучшее решение, но, чтобы минимально избежать ошибок, сработает"""
        if task.status in (TaskStatus.PENDING, TaskStatus.PROCESSING):
            return False
        await self.session.delete(task)
        await self.session.commit()
        return True
