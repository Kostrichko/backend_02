from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from database import get_session
from service.task_service import TaskService
from shared.schemas import TaskCreate, TaskUpdate, TaskResponse


router = APIRouter(tags=["tasks"])


async def get_task_session(session=Depends(get_session)):
    return TaskService(session)


@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def create_task(
    task_data: TaskCreate,
    service: TaskService = Depends(get_task_session),
):
    task = await service.create_task(task_data)
    return {"task_id": task.id, "status": task.status}


@router.get("/", response_model=List[TaskResponse])
async def get_all_tasks(service: TaskService = Depends(get_task_session)):
    return await service.get_all_tasks()


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, service: TaskService = Depends(get_task_session)):
    task = await service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    service: TaskService = Depends(get_task_session),
):
    task = await service.update_task(task_id, task_data)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, service: TaskService = Depends(get_task_session)):
    if not await service.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
