"""
Training Portal Schemas

Pydantic models for requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime
from uuid import UUID


# ==================== USER SCHEMAS ====================

class UserCreate(BaseModel):
    """Create user request."""
    email: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserApprove(BaseModel):
    """Approve user request."""
    ohr_id: str = Field(..., description="OHR ID (e.g., john@company.com)")


class UserResponse(BaseModel):
    """User response."""
    id: UUID
    keycloak_id: str
    email: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    ohr_id: Optional[str] = None
    assigned_role: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """List of users."""
    users: List[UserResponse]
    total: int


# ==================== AUTH SCHEMAS ====================

class TokenExchangeRequest(BaseModel):
    """Token exchange request."""
    code: str
    redirect_uri: str


# ==================== TASK SCHEMAS ====================

class TaskCreate(BaseModel):
    """Create task request."""
    name: str
    description: Optional[str] = None
    priority: str = "MEDIUM"
    due_date: Optional[datetime] = None
    is_recurring: bool = False
    recurrence_pattern: str = "ONCE"


class TaskUpdate(BaseModel):
    """Update task request."""
    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None


class TaskAssign(BaseModel):
    """Assign task request."""
    assigned_to: UUID


class TaskResponse(BaseModel):
    """Task response."""
    id: UUID
    name: str
    description: Optional[str] = None
    status: str
    priority: str
    created_at: datetime
    assigned_to: Optional[UUID] = None
    due_date: Optional[datetime] = None
    is_recurring: bool
    recurrence_pattern: str

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """List of tasks."""
    tasks: List[TaskResponse]
    total: int


# ==================== SUBMISSION SCHEMAS ====================

class SubmissionCreate(BaseModel):
    """Create submission request."""
    task_id: UUID
    notes: Optional[str] = None
    file_references: List[str] = []
    links: List[str] = []


class SubmissionReview(BaseModel):
    """Review submission request."""
    review_status: str = Field(..., pattern="^(APPROVED|REJECTED)$")
    review_comments: Optional[str] = None


class SubmissionResponse(BaseModel):
    """Submission response."""
    id: UUID
    task_id: UUID
    submitted_by: UUID
    submitted_at: datetime
    notes: Optional[str] = None
    file_references: List[str] = []
    links: List[str] = []
    review_status: str
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    review_comments: Optional[str] = None

    class Config:
        from_attributes = True


class SubmissionListResponse(BaseModel):
    """List of submissions."""
    submissions: List[SubmissionResponse]
    total: int


# ==================== RBAC SCHEMAS ====================

class RoleResponse(BaseModel):
    """Role response."""
    id: UUID
    name: str
    description: Optional[str] = None
    is_system: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PermissionResponse(BaseModel):
    """Permission response."""
    id: UUID
    name: str
    resource: str
    action: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== RESPONSE WRAPPERS ====================

class SuccessResponse(BaseModel):
    """Success response wrapper."""
    success: bool = True
    data: Optional[Any] = None
    message: str = "Operation successful"
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": None,
                "message": "Operation successful",
                "timestamp": "2024-01-02T15:30:00"
            }
        }


class ErrorResponse(BaseModel):
    """Error response wrapper."""
    success: bool = False
    error: str
    code: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "User not found",
                "code": "NOT_FOUND",
                "timestamp": "2024-01-02T15:30:00"
            }
        }


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    success: bool = True
    data: List[Any]
    pagination: Dict[str, int]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": [],
                "pagination": {"total": 0, "page": 1, "per_page": 20},
                "timestamp": "2024-01-02T15:30:00"
            }
        }