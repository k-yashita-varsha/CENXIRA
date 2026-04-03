"""
Utility functions and constants.

Constants, custom exceptions, validators, and helper functions.
"""

from typing import Optional
from datetime import datetime
from uuid import UUID
from fastapi import HTTPException, status
import re


# ==================== CONSTANTS ====================

class RoleConstants:
    """Built-in roles."""
    ADMIN = "admin"
    MANAGER = "manager"
    TRAINEE = "trainee"
    
    ALL = [ADMIN, MANAGER, TRAINEE]


class PermissionConstants:
    """Built-in permissions in resource:action format."""
    
    # User permissions
    USERS_APPROVE = "users:approve"
    USERS_REJECT = "users:reject"
    USERS_VIEW_ALL = "users:view_all"
    USERS_UPDATE = "users:update"
    USERS_DELETE = "users:delete"
    
    # Task permissions
    TASKS_CREATE = "tasks:create"
    TASKS_VIEW = "tasks:view"
    TASKS_VIEW_ALL = "tasks:view_all"
    TASKS_UPDATE = "tasks:update"
    TASKS_DELETE = "tasks:delete"
    TASKS_ASSIGN = "tasks:assign"
    
    # Submission permissions
    SUBMISSIONS_CREATE = "submissions:create"
    SUBMISSIONS_VIEW = "submissions:view"
    SUBMISSIONS_REVIEW = "submissions:review"
    
    # Report permissions
    REPORTS_VIEW = "reports:view"
    REPORTS_VIEW_ALL = "reports:view_all"


class StatusConstants:
    """User statuses."""
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"
    INACTIVE = "INACTIVE"
    
    ALL = [PENDING, ACTIVE, REJECTED, INACTIVE]


class TaskStatusConstants:
    """Task statuses."""
    BACKLOG = "BACKLOG"
    IN_PROGRESS = "IN_PROGRESS"
    UNDER_REVIEW = "UNDER_REVIEW"
    COMPLETED = "COMPLETED"
    
    ALL = [BACKLOG, IN_PROGRESS, UNDER_REVIEW, COMPLETED]


class ReviewStatusConstants:
    """Submission review statuses."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    
    ALL = [PENDING, APPROVED, REJECTED]


# ==================== EXCEPTIONS ====================

class AppException(Exception):
    """Base application exception."""
    
    def __init__(self, message: str, code: str = "APP_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundError(AppException):
    """Resource not found."""
    
    def __init__(self, message: str):
        super().__init__(message, "NOT_FOUND", 404)


class ValidationError(AppException):
    """Validation error."""
    
    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR", 400)


class UnauthorizedError(AppException):
    """User not authenticated."""
    
    def __init__(self, message: str = "Not authenticated"):
        super().__init__(message, "UNAUTHORIZED", 401)


class ForbiddenError(AppException):
    """User lacks permission."""
    
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, "FORBIDDEN", 403)


class ConflictError(AppException):
    """Resource already exists."""
    
    def __init__(self, message: str):
        super().__init__(message, "CONFLICT", 409)


# ==================== VALIDATORS ====================

class EmailValidator:
    """Email validation."""
    
    @staticmethod
    def validate(email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def is_company_email(email: str, company_domain: str) -> bool:
        """Check if email is from company domain."""
        if "@" not in email:
            return False
        domain = email.split("@")[1]
        return domain == company_domain


class DateValidator:
    """Date validation."""
    
    @staticmethod
    def validate_future_date(date: datetime) -> bool:
        """Validate date is in future."""
        return date > datetime.utcnow()
    
    @staticmethod
    def validate_due_date(due_date: Optional[datetime]) -> bool:
        """Validate due date."""
        if not due_date:
            return True
        return due_date > datetime.utcnow()


class PriorityValidator:
    """Priority validation."""
    
    VALID_PRIORITIES = ["LOW", "MEDIUM", "HIGH"]
    
    @staticmethod
    def validate(priority: str) -> bool:
        """Validate priority."""
        return priority in PriorityValidator.VALID_PRIORITIES


class StatusValidator:
    """Status validation."""
    
    @staticmethod
    def validate_user_status(status: str) -> bool:
        """Validate user status."""
        return status in StatusConstants.ALL
    
    @staticmethod
    def validate_task_status(status: str) -> bool:
        """Validate task status."""
        return status in TaskStatusConstants.ALL


# ==================== HELPERS ====================

def raise_not_found(resource: str, identifier: str) -> None:
    """Raise NotFoundError."""
    raise NotFoundError(f"{resource} not found: {identifier}")


def raise_validation_error(message: str) -> None:
    """Raise ValidationError."""
    raise ValidationError(message)


def raise_forbidden(message: str = "Permission denied") -> None:
    """Raise ForbiddenError."""
    raise ForbiddenError(message)


def raise_conflict(message: str) -> None:
    """Raise ConflictError."""
    raise ConflictError(message)


def to_uuid(value: str) -> UUID:
    """Convert string to UUID."""
    try:
        return UUID(value)
    except ValueError:
        raise_validation_error(f"Invalid UUID: {value}")


def get_http_exception(exc: AppException) -> HTTPException:
    """Convert AppException to HTTPException."""
    return HTTPException(
        status_code=exc.status_code,
        detail={
            "error": exc.message,
            "code": exc.code,
        }
    )