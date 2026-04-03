"""
Taskflow Models

Data classes, enums, and Pydantic models for task management.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from uuid import uuid4
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ==================== ENUMS ====================

class TaskStatus(str, Enum):
    """Task workflow status."""
    BACKLOG = "BACKLOG"
    IN_PROGRESS = "IN_PROGRESS"
    UNDER_REVIEW = "UNDER_REVIEW"
    COMPLETED = "COMPLETED"


class Priority(str, Enum):
    """Task priority levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RecurrencePattern(str, Enum):
    """Task recurrence patterns."""
    ONCE = "ONCE"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class ReviewStatus(str, Enum):
    """Submission review status."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# ==================== DATA CLASSES ====================

@dataclass
class Task:
    """
    Task representation.
    
    Attributes:
        id: Unique task identifier
        name: Task name
        description: Detailed description
        status: Current task status (BACKLOG, IN_PROGRESS, UNDER_REVIEW, COMPLETED)
        priority: Task priority (LOW, MEDIUM, HIGH)
        created_by: User ID who created task
        assigned_to: User ID assigned to task
        due_date: Due date for completion
        created_at: Creation timestamp
        updated_at: Last update timestamp
        is_recurring: Whether task recurs
        recurrence_pattern: Recurrence pattern (ONCE, DAILY, WEEKLY, MONTHLY)
        recurrence_last_run: Last run timestamp for recurring tasks
        metadata: Additional task metadata
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = field(default="")
    description: str = field(default="")
    status: str = field(default="PENDING")
    priority: str = field(default="MEDIUM")
    created_by: str = field(default="")
    assigned_to: Optional[str] = field(default=None)
    due_date: Optional[datetime] = field(default=None)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_recurring: bool = field(default=False)
    recurrence_pattern: str = field(default="ONCE")
    recurrence_last_run: Optional[datetime] = field(default=None)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate task data."""
        if not self.name:
            raise ValueError("Task name cannot be empty")
        if len(self.name) < 3:
            raise ValueError("Task name must be at least 3 characters")
        if self.status not in [s.value for s in TaskStatus]:
            raise ValueError(f"Invalid status: {self.status}")
        if self.priority not in [p.value for p in Priority]:
            raise ValueError(f"Invalid priority: {self.priority}")

    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if not self.due_date:
            return False
        return datetime.now() > self.due_date and self.status != TaskStatus.COMPLETED

    @property
    def is_due_soon(self) -> bool:
        """Check if task is due in next 24 hours."""
        if not self.due_date:
            return False
        diff = self.due_date - datetime.now()
        return timedelta(0) < diff <= timedelta(days=1)


@dataclass
class Submission:
    """
    Task submission representation.
    
    Attributes:
        id: Unique submission identifier
        task_id: Associated task ID
        submitted_by: User ID who submitted
        submitted_at: Submission timestamp
        notes: Submission notes/comments
        file_references: List of file references (URLs, paths)
        links: Additional links/references
        review_status: Review status (PENDING, APPROVED, REJECTED)
        reviewed_by: User ID who reviewed
        reviewed_at: Review timestamp
        review_comments: Reviewer comments
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    task_id: str = field(default="")
    submitted_by: str = field(default="")
    submitted_at: datetime = field(default_factory=datetime.now)
    notes: str = field(default="")
    file_references: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    review_status: str = field(default="PENDING")
    reviewed_by: Optional[str] = field(default=None)
    reviewed_at: Optional[datetime] = field(default=None)
    review_comments: str = field(default="")

    def __post_init__(self):
        """Validate submission."""
        if not self.task_id:
            raise ValueError("Task ID cannot be empty")
        if not self.submitted_by:
            raise ValueError("Submitted by cannot be empty")


@dataclass
class AuditEvent:
    """
    Audit log entry.
    
    Tracks all changes to tasks and submissions.
    
    Attributes:
        id: Event identifier
        entity_type: Type of entity (task, submission, etc)
        entity_id: ID of entity being audited
        action: Action performed (create, update, delete, etc)
        actor: User ID who performed action
        changes: Dict of field changes (old -> new)
        timestamp: When action occurred
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    entity_type: str = field(default="")
    entity_id: str = field(default="")
    action: str = field(default="")
    actor: str = field(default="")
    changes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate audit event."""
        if not self.entity_type:
            raise ValueError("Entity type cannot be empty")
        if not self.entity_id:
            raise ValueError("Entity ID cannot be empty")
        if not self.action:
            raise ValueError("Action cannot be empty")


# ==================== EXCEPTIONS ====================

class TaskflowException(Exception):
    """Base exception for taskflow errors."""
    
    def __init__(self, message: str, code: str = "TASKFLOW_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class TaskNotFoundError(TaskflowException):
    """Raised when task is not found."""
    
    def __init__(self, task_id: str):
        super().__init__(f"Task not found: {task_id}", "TASK_NOT_FOUND")


class SubmissionNotFoundError(TaskflowException):
    """Raised when submission is not found."""
    
    def __init__(self, submission_id: str):
        super().__init__(f"Submission not found: {submission_id}", "SUBMISSION_NOT_FOUND")


class InvalidTransitionError(TaskflowException):
    """Raised when invalid state transition attempted."""
    
    def __init__(self, current_status: str, target_status: str):
        super().__init__(
            f"Cannot transition from {current_status} to {target_status}",
            "INVALID_TRANSITION"
        )


class TaskAlreadyAssignedError(TaskflowException):
    """Raised when trying to assign already assigned task."""
    
    def __init__(self, task_id: str):
        super().__init__(f"Task already assigned: {task_id}", "TASK_ALREADY_ASSIGNED")


class TaskNotAssignedError(TaskflowException):
    """Raised when task operation requires assignment but task not assigned."""
    
    def __init__(self, task_id: str):
        super().__init__(f"Task not assigned: {task_id}", "TASK_NOT_ASSIGNED")


class NoActiveSubmissionError(TaskflowException):
    """Raised when task has no active submission."""
    
    def __init__(self, task_id: str):
        super().__init__(f"No active submission for task: {task_id}", "NO_SUBMISSION")


class ValidationError(TaskflowException):
    """Raised when task validation fails."""
    
    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR")


class RepositoryError(TaskflowException):
    """Raised when repository operation fails."""
    
    def __init__(self, message: str):
        super().__init__(message, "REPOSITORY_ERROR")


class UnauthorizedError(TaskflowException):
    """Raised when user unauthorized for operation."""
    
    def __init__(self, message: str = "User not authorized"):
        super().__init__(message, "UNAUTHORIZED")


# ==================== PYDANTIC MODELS ====================

class TaskSchema(BaseModel):
    """Pydantic schema for task responses."""
    id: str
    name: str
    description: Optional[str] = None
    status: str
    priority: str
    created_by: str
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    is_recurring: bool
    recurrence_pattern: str


class SubmissionSchema(BaseModel):
    """Pydantic schema for submission responses."""
    id: str
    task_id: str
    submitted_by: str
    submitted_at: datetime
    notes: Optional[str] = None
    file_references: List[str] = []
    links: List[str] = []
    review_status: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_comments: Optional[str] = None


class AuditLogSchema(BaseModel):
    """Pydantic schema for audit log responses."""
    id: str
    entity_type: str
    entity_id: str
    action: str
    actor: str
    changes: Dict[str, Any]
    timestamp: datetime