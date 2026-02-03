from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict
from shared.models.task import TaskStatus


class TaskCreate(BaseModel):
    payload: str


class TaskUpdate(BaseModel):
    payload: str | None = None
    status: TaskStatus | None = None
    result: str | None = None


class TaskMessage(BaseModel):
    """ для очереди"""
    task_id: int

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, data: str) -> "TaskMessage":
        return cls.model_validate_json(data)


class TaskResponse(BaseModel):
    id: int
    payload: str
    status: TaskStatus
    result: str | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TaskStatusResponse(BaseModel):
    task_id: int
    status: TaskStatus
