"""
Taskflow System Package

Production-ready task management and workflow engine with state machines,
recurring tasks, submissions, and comprehensive audit logging.

Example:
    from taskflow_system.service import TaskService, TaskStateMachine
    from taskflow_system.models import TaskStatus, Priority, Task
    from taskflow_system.schemas import TaskCreate, TaskResponse
    
    # Initialize service with your repository
    service = TaskService(your_repository)
    
    # Create task
    task_data = TaskCreate(
        name="Review documents",
        priority=Priority.HIGH,
        due_date="2024-12-31"
    )
    task = service.create_task(task_data, created_by="user_id")
    
    # Assign to user
    service.assign_task(task.id, "assignee_id")
    
    # Submit task
    service.submit_task(task.id, "submitter_id")
    
    # Approve submission
    service.approve_submission(task.id, "reviewer_id")
"""

__version__ = "1.0.0"
__author__ = "Training Portal Team"

from taskflow_system.config import TaskflowConfig
from taskflow_system.models import (
    Task,
    Submission,
    AuditEvent,
    TaskStatus,
    Priority,
    RecurrencePattern,
    ReviewStatus,
)
from taskflow_system.service import TaskService, TaskStateMachine, TaskValidator
from taskflow_system.repository import TaskRepository, AuditLogger
from taskflow_system.schemas import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    SubmissionCreate,
    SubmissionResponse,
    AuditLogResponse,
)

__all__ = [
    "TaskflowConfig",
    "Task",
    "Submission",
    "AuditEvent",
    "TaskStatus",
    "Priority",
    "RecurrencePattern",
    "ReviewStatus",
    "TaskService",
    "TaskStateMachine",
    "TaskValidator",
    "TaskRepository",
    "AuditLogger",
    "TaskCreate",
    "TaskUpdate",
    "TaskResponse",
    "SubmissionCreate",
    "SubmissionResponse",
    "AuditLogResponse",
]