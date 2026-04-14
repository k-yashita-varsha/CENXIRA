from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from uuid import UUID

from app.database import get_db, Task, Submission, User, TaskStatusConstants, ReviewStatusConstants
from app.schemas import SuccessResponse, SubmissionCreate

from keycloak_auth import get_current_user, AuthenticatedUser
from rbac_system import require_role
from taskflow_system.service import TaskStateMachine

router = APIRouter(prefix="/trainee", tags=["Trainee"])

@router.get("/progress", response_model=SuccessResponse)
async def get_my_progress(
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("Trainee"))
):
    """Calculate task completion percentage for the trainee."""
    # 1. Resolve Local DB ID
    stmt = select(User.id).where(User.keycloak_id == current_user.user_id)
    res = await db.execute(stmt)
    local_id = res.scalar()
    
    if not local_id:
        return SuccessResponse(data={"completion_percentage": 0})

    # 2. Get counts
    stmt = select(Task).where(Task.assigned_to == local_id)
    res = await db.execute(stmt)
    tasks = res.scalars().all()
    
    total = len(tasks)
    completed = len([t for t in tasks if t.status == TaskStatusConstants.COMPLETED])
    
    percentage = (completed / total * 100) if total > 0 else 0
    return SuccessResponse(data={"completion_percentage": round(percentage, 1)})

@router.get("/tasks", response_model=SuccessResponse)
async def list_assigned_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("Trainee"))
):
    """List tasks assigned to the current trainee with Manager names."""
    # 1. Resolve Local DB ID - Enhanced lookup
    stmt = select(User).where(User.keycloak_id == current_user.user_id)
    res = await db.execute(stmt)
    local_user = res.scalars().first()
    
    if not local_user:
        logger.warning(f"Trainee {current_user.user_id} has no local DB profile.")
        return SuccessResponse(data=[])

    # 2. Filter by Local ID and Join with Creator (Manager)
    from sqlalchemy.orm import aliased
    Manager = aliased(User)
    
    stmt = (
        select(Task, Manager.first_name, Manager.last_name, Manager.ohr_id)
        .outerjoin(Manager, Task.created_by == Manager.id)
        .where(Task.assigned_to == local_user.id)
    )
    result = await db.execute(stmt)
    rows = result.all()
    
    from app.schemas import TaskResponse
    data = []
    for task, fn, ln, ohr in rows:
        task_data = TaskResponse.model_validate(task).model_dump()
        # Add creator info if dashboard wants to show "Assigned By"
        if fn or ln:
            task_data["created_by_name"] = f"{fn or ''} {ln or ''}".strip()
        data.append(task_data)
        
    return SuccessResponse(data=data)


@router.post("/tasks/{task_id}/start", response_model=SuccessResponse)
async def start_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("Trainee"))
):
    """Start a task (Change status to IN PROGRESS)."""
    # Resolve local ID
    stmt = select(User.id).where(User.keycloak_id == current_user.user_id)
    res = await db.execute(stmt)
    local_id = res.scalar()

    stmt = select(Task).where(Task.id == task_id, Task.assigned_to == local_id)
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
    # Resolve local ID
    stmt = select(User.id).where(User.keycloak_id == current_user.user_id)
    res = await db.execute(stmt)
    local_id = res.scalar()

    stmt = select(Task).where(Task.id == task_id, Task.assigned_to == local_id)
    result = await db.execute(stmt)
    task = result.scalars().first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or not assigned to you.")
        
    TaskStateMachine.validate_transition(task.status, TaskStatusConstants.UNDER_REVIEW)
    task.status = TaskStatusConstants.UNDER_REVIEW
    
    # Resolve Local DB ID for submission
    stmt = select(User.id).where(User.keycloak_id == current_user.user_id)
    res = await db.execute(stmt)
    local_id = res.scalar()

    # Create submission record
    new_submission = Submission(
        task_id=task_id,
        submitted_by=local_id, # Use local ID
        notes=req.notes,
        submission_text=req.submission_text,
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
    """List all submissions by the trainee with task names."""
    # Resolve Local DB ID
    stmt = select(User.id).where(User.keycloak_id == current_user.user_id)
    res = await db.execute(stmt)
    local_id = res.scalar()

    # Join Submission with Task to get Task Name
    stmt = (
        select(Submission, Task.name)
        .join(Task, Submission.task_id == Task.id)
        .where(Submission.submitted_by == local_id)
    )
    result = await db.execute(stmt)
    rows = result.all()
    
    from app.schemas import SubmissionResponse
    data = []
    for sub, tname in rows:
        sub_data = SubmissionResponse.model_validate(sub).model_dump()
        sub_data["task_name"] = tname
        sub_data["created_at"] = sub.submitted_at
        data.append(sub_data)
        
    return SuccessResponse(data=data)
