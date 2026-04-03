from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from uuid import UUID

from app.database import get_db, Task, Submission, TaskStatusConstants, ReviewStatusConstants
from app.schemas import SuccessResponse, SubmissionCreate

from keycloak_auth import get_current_user, AuthenticatedUser
from rbac_system import require_role
from taskflow_system.service import TaskStateMachine

router = APIRouter(prefix="/trainee", tags=["Trainee"])

@router.get("/tasks", response_model=SuccessResponse)
async def list_assigned_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("Trainee"))
):
    """List tasks assigned to the current trainee."""
    stmt = select(Task).where(Task.assigned_to == current_user.user_id)
    result = await db.execute(stmt)
    tasks = result.scalars().all()
    
    from app.schemas import TaskResponse
    data = [TaskResponse.model_validate(t).model_dump() for t in tasks]
    return SuccessResponse(data=data)


@router.post("/tasks/{task_id}/start", response_model=SuccessResponse)
async def start_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("Trainee"))
):
    """Start a task (Change status to IN PROGRESS)."""
    stmt = select(Task).where(Task.id == task_id, Task.assigned_to == current_user.user_id)
    result = await db.execute(stmt)
    task = result.scalars().first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or not assigned to you.")
        
    TaskStateMachine.validate_transition(task.status, TaskStatusConstants.IN_PROGRESS)
    task.status = TaskStatusConstants.IN_PROGRESS
    
    await db.commit()
    return SuccessResponse(message="Task started successfully.")


@router.post("/tasks/{task_id}/submit", response_model=SuccessResponse)
async def submit_task(
    task_id: UUID,
    req: SubmissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("Trainee"))
):
    """Submit work for a task."""
    stmt = select(Task).where(Task.id == task_id, Task.assigned_to == current_user.user_id)
    result = await db.execute(stmt)
    task = result.scalars().first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or not assigned to you.")
        
    TaskStateMachine.validate_transition(task.status, TaskStatusConstants.UNDER_REVIEW)
    task.status = TaskStatusConstants.UNDER_REVIEW
    
    # Create submission record
    new_submission = Submission(
        task_id=task_id,
        submitted_by=current_user.user_id,
        notes=req.notes,
        file_references=req.file_references,
        links=req.links,
        review_status=ReviewStatusConstants.PENDING
    )
    db.add(new_submission)
    
    await db.commit()
    return SuccessResponse(message="Task submitted for review successfully.")


@router.get("/submissions", response_model=SuccessResponse)
async def list_my_submissions(
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("Trainee"))
):
    """List all submissions by the trainee."""
    stmt = select(Submission).where(Submission.submitted_by == current_user.user_id)
    result = await db.execute(stmt)
    submissions = result.scalars().all()
    
    from app.schemas import SubmissionResponse
    data = [SubmissionResponse.model_validate(s).model_dump() for s in submissions]
    return SuccessResponse(data=data)
