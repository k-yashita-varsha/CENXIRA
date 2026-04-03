"""
Models Module.

All SQLAlchemy ORM models (User, Task, Submission, Role, Permission) 
have been placed directly inside `app/database.py` by the builder to avoid circular imports.
We import them here so that you can also import them from `app.models`.
"""

from app.database import (
    Base,
    TimestampMixin,
    User,
    Role,
    Permission,
    UserRole,
    RolePermission,
    Task,
    Submission,
    AuditLog
)

__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "Role",
    "Permission",
    "UserRole",
    "RolePermission",
    "Task",
    "Submission",
    "AuditLog"
]
