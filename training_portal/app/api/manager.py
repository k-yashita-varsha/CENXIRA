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
    """Create a new task and optionally assign it."""
    # 1. Resolve the Manager's Local DB ID (Fixes ForeignKeyViolation)
    stmt = select(User).where(User.keycloak_id == current_user.user_id)
    res = await db.execute(stmt)
    manager_user = res.scalars().first()
    
    if not manager_user:
        raise HTTPException(
            status_code=404, 
            detail="Manager profile not found in local database. Please contact Admin."
        )

    # 2. If assigned_to is provided, verify they are a trainee
    if req.assigned_to:
        stmt = select(User).where(User.id == req.assigned_to, User.assigned_role == "Trainee")
        res = await db.execute(stmt)
        trainee = res.scalars().first()
        if not trainee:
            raise HTTPException(status_code=400, detail="Assignment failed: User is not a trainee or does not exist.")

    # 3. Create the task using the local manager_user.id
    new_task = Task(
        name=req.name,
        description=req.description,
        status=TaskStatusConstants.BACKLOG if not req.assigned_to else TaskStatusConstants.IN_PROGRESS,
        priority=req.priority,
        created_by=manager_user.id, # Use local ID, not Keycloak ID
        assigned_to=req.assigned_to,
        due_date=req.due_date,
        is_recurring=req.is_recurring,
        recurrence_pattern=req.recurrence_pattern
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    
    return SuccessResponse(message="Task created successfully.", data={"task_id": str(new_task.id)})

@router.get("/trainees", response_model=SuccessResponse)
async def list_trainees(
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("Manager"))
):
    """List all active trainees for assignment with task counts."""
    stmt = select(User).where(User.assigned_role == "Trainee", User.status == "ACTIVE")
    result = await db.execute(stmt)
    trainees = result.scalars().all()
    
    data = []
    for t in trainees:
        # Count tasks assigned to this specific trainee
        count_stmt = select(Task.id).where(Task.assigned_to == t.id)
        count_res = await db.execute(count_stmt)
        task_count = len(count_res.scalars().all())
        
        data.append({
            "id": str(t.id),
            "email": t.email,
            "name": f"{t.ohr_id} - {t.first_name} {t.last_name}" if t.ohr_id else t.email,
            "ohr_id": t.ohr_id,
            "tasks_count": task_count,
            "role": "Trainee"
        })
    return SuccessResponse(data=data)


@router.get("/tasks", response_model=SuccessResponse)
async def list_manager_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("Manager"))
):
    """List tasks created by this manager with trainee names."""
    # 1. Resolve Local DB ID
    stmt = select(User.id).where(User.keycloak_id == current_user.user_id)
    res = await db.execute(stmt)
    local_id = res.scalar()
    
    if not local_id:
        return SuccessResponse(data=[])

    # 2. Filter by Local ID and Join with Users to get trainee names
    # We join User on Task.assigned_to to get the assignee's details
    from sqlalchemy.orm import aliased
    Trainee = aliased(User)
    
    stmt = (
        select(Task, Trainee.first_name, Trainee.last_name, Trainee.ohr_id)
        .outerjoin(Trainee, Task.assigned_to == Trainee.id)
        .where(Task.created_by == local_id)
    )
    result = await db.execute(stmt)
    rows = result.all()
    
    data = []
    for task, fn, ln, ohr in rows:
        task_data = TaskResponse.model_validate(task).model_dump()
        if fn or ln:
            task_data["assigned_to_name"] = f"{fn or ''} {ln or ''}".strip()
        if ohr:
            task_data["assigned_to_ohrid"] = ohr
            # Also update name to include OHRID for the dashboard if it expects it
            if task_data["assigned_to_name"]:
                task_data["assigned_to_name"] = f"{ohr} - {task_data['assigned_to_name']}"
            else:
                task_data["assigned_to_name"] = ohr
        data.append(task_data)
        
    return SuccessResponse(data=data)


@router.post("/tasks/{task_id}/assign", response_model=SuccessResponse)
async def assign_task(
    task_id: UUID,
    req: TaskAssign,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("Manager"))
):
    """Assign task to a trainee."""
    # Resolve local ID
    stmt = select(User.id).where(User.keycloak_id == current_user.user_id)
    res = await db.execute(stmt)
    local_id = res.scalar()

    stmt = select(Task).where(Task.id == task_id, Task.created_by == local_id)
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
    """List pending submissions for tasks created by this manager with names."""
    # Resolve local ID
    stmt = select(User.id).where(User.keycloak_id == current_user.user_id)
    res = await db.execute(stmt)
    local_id = res.scalar()

    # Find Task IDs + Names
    stmt = select(Task.id, Task.name).where(Task.created_by == local_id)
    result = await db.execute(stmt)
    task_info = result.all()
    task_map = {tid: tname for tid, tname in task_info}
    task_ids = list(task_map.keys())
    
    if not task_ids:
        return SuccessResponse(data=[])
        
    # Join Submission with User to get submitter name
    sub_stmt = (
        select(Submission, User.first_name, User.last_name, User.ohr_id)
        .join(User, Submission.submitted_by == User.id)
        .where(
            Submission.task_id.in_(task_ids),
            Submission.review_status == ReviewStatusConstants.PENDING
        )
    )
    sub_result = await db.execute(sub_stmt)
    rows = sub_result.all()
    
    from app.schemas import SubmissionResponse
    data = []
    for sub, fn, ln, ohr in rows:
        sub_data = SubmissionResponse.model_validate(sub).model_dump()
        sub_data["task_name"] = task_map.get(sub.task_id, "Unknown Task")
        sub_data["submitted_by_name"] = f"{ohr} - {fn or ''} {ln or ''}".strip() if ohr else f"{fn or ''} {ln or ''}".strip()
        # Fallback for frontend fields
        sub_data["submission_text"] = sub.notes
        sub_data["created_at"] = sub.submitted_at
        data.append(sub_data)
        
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
        
    # Resolve local ID
    stmt = select(User.id).where(User.keycloak_id == current_user.user_id)
    res = await db.execute(stmt)
    local_id = res.scalar()

    task_stmt = select(Task).where(Task.id == submission.task_id)
    task_result = await db.execute(task_stmt)
    task = task_result.scalars().first()
    
    if task.created_by != local_id:
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
