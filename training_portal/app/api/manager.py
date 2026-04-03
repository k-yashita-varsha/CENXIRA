from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from uuid import UUID

from app.database import get_db, Task, Submission, User, TaskStatusConstants, ReviewStatusConstants
from app.schemas import SuccessResponse, TaskCreate, TaskAssign, SubmissionReview

from keycloak_auth import get_current_user, AuthenticatedUser
from rbac_system import require_role
from taskflow_system.service import TaskStateMachine

router = APIRouter(prefix="/manager", tags=["Manager"])


@router.post("/tasks", response_model=SuccessResponse)
async def create_task(
    req: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("Manager"))
):
    """Create a new task."""
    new_task = Task(
        name=req.name,
        description=req.description,
        status=TaskStatusConstants.BACKLOG,
        priority=req.priority,
        created_by=current_user.user_id,
        due_date=req.due_date,
        is_recurring=req.is_recurring,
        recurrence_pattern=req.recurrence_pattern
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    
    return SuccessResponse(message="Task created successfully.", data={"task_id": str(new_task.id)})


@router.get("/tasks", response_model=SuccessResponse)
async def list_manager_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("Manager"))
):
    """List tasks created by this manager."""
    stmt = select(Task).where(Task.created_by == current_user.user_id)
    result = await db.execute(stmt)
    tasks = result.scalars().all()
    
    from app.schemas import TaskResponse
    data = [TaskResponse.model_validate(t).model_dump() for t in tasks]
    return SuccessResponse(data=data)


@router.post("/tasks/{task_id}/assign", response_model=SuccessResponse)
async def assign_task(
    task_id: UUID,
    req: TaskAssign,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("Manager"))
):
    """Assign task to a trainee."""
    stmt = select(Task).where(Task.id == task_id, Task.created_by == current_user.user_id)
    result = await db.execute(stmt)
    task = result.scalars().first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or not owned by you.")
        
    if task.assigned_to:
        raise HTTPException(status_code=400, detail="Task already assigned.")
        
    task.assigned_to = req.assigned_to
    await db.commit()
    return SuccessResponse(message="Task assigned successfully.")


@router.get("/submissions", response_model=SuccessResponse)
async def list_pending_submissions(
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("Manager"))
):
    """List pending submissions for tasks created by this manager."""
    # Find all tasks created by the manager
    stmt = select(Task.id).where(Task.created_by == current_user.user_id)
    result = await db.execute(stmt)
    task_ids = result.scalars().all()
    
    if not task_ids:
        return SuccessResponse(data=[])
        
    sub_stmt = select(Submission).where(
        Submission.task_id.in_(task_ids),
        Submission.review_status == ReviewStatusConstants.PENDING
    )
    sub_result = await db.execute(sub_stmt)
    submissions = sub_result.scalars().all()
    
    from app.schemas import SubmissionResponse
    data = [SubmissionResponse.model_validate(s).model_dump() for s in submissions]
    return SuccessResponse(data=data)


@router.post("/submissions/{submission_id}/review", response_model=SuccessResponse)
async def review_submission(
    submission_id: UUID,
    req: SubmissionReview,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("Manager"))
):
    """Approve or reject a submission."""
    sub_stmt = select(Submission).where(Submission.id == submission_id)
    sub_result = await db.execute(sub_stmt)
    submission = sub_result.scalars().first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")
        
    task_stmt = select(Task).where(Task.id == submission.task_id)
    task_result = await db.execute(task_stmt)
    task = task_result.scalars().first()
    
    if task.created_by != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to review this submission.")
        
    # Apply state machine transition
    # PENDING means Task was UNDER_REVIEW
    target_state = TaskStatusConstants.COMPLETED if req.review_status == ReviewStatusConstants.APPROVED else TaskStatusConstants.IN_PROGRESS
    
    TaskStateMachine.validate_transition(task.status, target_state)
    
    task.status = target_state
    
    submission.review_status = req.review_status
    submission.review_comments = req.review_comments
    submission.reviewed_by = current_user.user_id
    
    await db.commit()
    return SuccessResponse(message=f"Submission {req.review_status.lower()} successfully.")
