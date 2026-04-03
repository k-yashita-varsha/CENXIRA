"""
Taskflow Pydantic Schemas

Request/response schemas for FastAPI integration.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


# ==================== TASK SCHEMAS ====================

class TaskCreate(BaseModel):
    """Create task request."""
    name: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    priority: str = Field(default="MEDIUM")
    due_date: Optional[datetime] = None
    is_recurring: bool = Field(default=False)
    recurrence_pattern: str = Field(default="ONCE")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Review training materials",
                "description": "Review and approve training materials",
                "priority": "HIGH",
                "due_date": "2024-12-31T17:00:00",
                "is_recurring": False,
                "recurrence_pattern": "ONCE",
            }
        }


class TaskUpdate(BaseModel):
    """Update task request."""
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    is_recurring: Optional[bool] = None
    recurrence_pattern: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "priority": "MEDIUM",
                "due_date": "2024-12-15T17:00:00",
            }
        }


class TaskResponse(BaseModel):
    """Task response."""
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
    is_overdue: bool = False
    is_due_soon: bool = False

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Review training materials",
                "status": "IN_PROGRESS",
                "priority": "HIGH",
                "created_by": "admin-user-id",
                "assigned_to": "trainee-user-id",
                "due_date": "2024-12-31T17:00:00",
                "created_at": "2024-01-01T10:00:00",
                "updated_at": "2024-01-02T15:30:00",
                "is_recurring": False,
                "recurrence_pattern": "ONCE",
            }
        }


class TaskListResponse(BaseModel):
    """List of tasks response."""
    tasks: List[TaskResponse]
    total: int


# ==================== SUBMISSION SCHEMAS ====================

class SubmissionCreate(BaseModel):
    """Create submission request."""
    notes: Optional[str] = Field(None, max_length=2000)
    file_references: List[str] = Field(default_factory=list)
    links: List[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "notes": "Training materials reviewed and approved",
                "file_references": [
                    "s3://bucket/materials/module-1.pdf",
                    "s3://bucket/materials/module-2.pdf"
                ],
                "links": ["https://training.company.com/module-1"]
            }
        }


class SubmissionResponse(BaseModel):
    """Submission response."""
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

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "650e8400-e29b-41d4-a716-446655440001",
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "submitted_by": "trainee-user-id",
                "submitted_at": "2024-01-15T14:30:00",
                "notes": "Materials reviewed successfully",
                "file_references": ["s3://bucket/submission/review.pdf"],
                "links": [],
                "review_status": "PENDING",
            }
        }


class SubmissionReviewRequest(BaseModel):
    """Review submission request."""
    review_status: str = Field(..., pattern="^(APPROVED|REJECTED)$")
    comments: Optional[str] = Field(None, max_length=2000)

    class Config:
        json_schema_extra = {
            "example": {
                "review_status": "APPROVED",
                "comments": "Excellent work, well done!"
            }
        }


class SubmissionListResponse(BaseModel):
    """List of submissions response."""
    submissions: List[SubmissionResponse]
    total: int


# ==================== AUDIT LOG SCHEMAS ====================

class AuditLogResponse(BaseModel):
    """Audit log response."""
    id: str
    entity_type: str
    entity_id: str
    action: str
    actor: str
    changes: Dict[str, Any]
    timestamp: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "750e8400-e29b-41d4-a716-446655440002",
                "entity_type": "task",
                "entity_id": "550e8400-e29b-41d4-a716-446655440000",
                "action": "status_change",
                "actor": "admin-user-id",
                "changes": {
                    "status": {
                        "old": "BACKLOG",
                        "new": "IN_PROGRESS"
                    }
                },
                "timestamp": "2024-01-02T15:30:00"
            }
        }


class AuditLogListResponse(BaseModel):
    """List of audit logs response."""
    logs: List[AuditLogResponse]
    total: int


# ==================== STATUS & ACTION RESPONSES ====================

class TaskActionResponse(BaseModel):
    """Generic task action response."""
    success: bool
    message: str
    data: Optional[TaskResponse] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Task status updated",
                "data": None
            }
        }


class ErrorResponse(BaseModel):
    """Error response."""
    success: bool = False
    error: str
    code: str
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "Task not found",
                "code": "TASK_NOT_FOUND",
                "timestamp": "2024-01-02T15:30:00"
            }
        }