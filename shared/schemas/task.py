from datetime import datetime
from pydantic import BaseModel, ConfigDict
from shared.models.task import TaskStatus


class TaskCreate(BaseModel):
    payload: str


class TaskUpdate(BaseModel):
    payload: str | None = None
    result: str | None = None


class TaskResponse(BaseModel):
    id: int
    payload: str
    status: TaskStatus
    result: str | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
