from typing import List
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from database import get_session
from service.task_service import TaskService
from shared.schemas import TaskCreate, TaskUpdate, TaskResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["tasks"])


async def get_task_session(session=Depends(get_session)):
    return TaskService(session)


@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def create_task(
    task_data: TaskCreate,
    service: TaskService = Depends(get_task_session)):
    logger.info(f"Creating task")
    task = await service.create_task(task_data)
    logger.info(f"Task {task.id} created successfully")
    return {"task_id": task.id, "status": task.status}


@router.get("/", response_model=List[TaskResponse])
async def get_all_tasks(
    skip: int = 0,
    limit: int = 100,
    service: TaskService = Depends(get_task_session)):
    """Get all tasks with pagination."""
    return await service.get_all_tasks(skip=skip, limit=limit)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, service: TaskService = Depends(get_task_session)):
    task = await service.get_task(task_id)
    if not task:
        logger.warning(f"Task {task_id} not found")
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    service: TaskService = Depends(get_task_session)):
    logger.info(f"Updating task {task_id}")
    task = await service.update_task(task_id, task_data)
    if not task:
        logger.warning(f"Task {task_id} not found")
        raise HTTPException(status_code=404, detail="Task not found")
    logger.info(f"Task {task_id} updated successfully")
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, service: TaskService = Depends(get_task_session)):
    logger.info(f"Deleting task {task_id}")
    if not await service.delete_task(task_id):
        logger.warning(f"Task {task_id} not found")
        raise HTTPException(status_code=404, detail="Task not found")
    logger.info(f"Task {task_id} deleted successfully")