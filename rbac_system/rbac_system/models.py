"""
RBAC Models

Data classes and Pydantic models for RBAC entities and exceptions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


# ==================== DATA CLASSES ====================

@dataclass
class Role:
    """
    Role representation.
    
    A role is a collection of permissions. Users can be assigned roles,
    and through roles they gain permissions.
    
    Attributes:
        id: Unique role identifier (UUID)
        name: Role name (must be unique)
        description: Human-readable description
        created_at: Creation timestamp
        updated_at: Last update timestamp
        is_system: Whether this is a system role (immutable)
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = field(default="")
    description: str = field(default="")
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_system: bool = field(default=False)

    def __post_init__(self):
        """Validate role data."""
        if not self.name:
            raise ValueError("Role name cannot be empty")
        if len(self.name) < 2:
            raise ValueError("Role name must be at least 2 characters")
        if len(self.name) > 100:
            raise ValueError("Role name cannot exceed 100 characters")

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other) -> bool:
        if isinstance(other, Role):
            return self.name == other.name
        return self.name == other


@dataclass
class Permission:
    """
    Permission representation.
    
    A permission is an action on a resource.
    Format: resource:action (e.g., "users:approve", "tasks:create")
    
    Attributes:
        id: Unique permission identifier
        name: Permission name (resource:action format)
        resource: Resource name (e.g., "users", "tasks", "reports")
        action: Action name (e.g., "create", "read", "update", "delete", "approve")
        description: Human-readable description
        created_at: Creation timestamp
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = field(default="")
    resource: str = field(default="")
    action: str = field(default="")
    description: str = field(default="")
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate permission data."""
        if not self.resource:
            raise ValueError("Resource cannot be empty")
        if not self.action:
            raise ValueError("Action cannot be empty")
        
        # Auto-generate name if not provided
        if not self.name:
            self.name = f"{self.resource}:{self.action}"

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other) -> bool:
        if isinstance(other, Permission):
            return self.name == other.name
        return self.name == other


@dataclass
class RolePermissionAssignment:
    """
    Assignment of a permission to a role.
    
    Attributes:
        id: Unique assignment identifier
        role_id: Role ID
        permission_id: Permission ID
        assigned_at: Assignment timestamp
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    role_id: str = field(default="")
    permission_id: str = field(default="")
    assigned_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate assignment."""
        if not self.role_id:
            raise ValueError("Role ID cannot be empty")
        if not self.permission_id:
            raise ValueError("Permission ID cannot be empty")


@dataclass
class UserRoleAssignment:
    """
    Assignment of a role to a user.
    
    Attributes:
        id: Unique assignment identifier
        user_id: User ID (from keycloak_auth)
        role_id: Role ID
        assigned_at: Assignment timestamp
        assigned_by: User ID who made the assignment (admin)
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = field(default="")
    role_id: str = field(default="")
    assigned_at: datetime = field(default_factory=datetime.now)
    assigned_by: Optional[str] = field(default=None)

    def __post_init__(self):
        """Validate assignment."""
        if not self.user_id:
            raise ValueError("User ID cannot be empty")
        if not self.role_id:
            raise ValueError("Role ID cannot be empty")


# ==================== EXCEPTIONS ====================

class RBACException(Exception):
    """Base exception for all RBAC errors."""
    
    def __init__(self, message: str, code: str = "RBAC_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class RoleNotFoundError(RBACException):
    """Raised when role is not found."""
    
    def __init__(self, role_id: str):
        super().__init__(f"Role not found: {role_id}", "ROLE_NOT_FOUND")


class PermissionNotFoundError(RBACException):
    """Raised when permission is not found."""
    
    def __init__(self, permission_id: str):
        super().__init__(f"Permission not found: {permission_id}", "PERMISSION_NOT_FOUND")


class RoleAlreadyExistsError(RBACException):
    """Raised when trying to create role that already exists."""
    
    def __init__(self, role_name: str):
        super().__init__(f"Role already exists: {role_name}", "ROLE_EXISTS")


class PermissionAlreadyExistsError(RBACException):
    """Raised when permission already exists."""
    
    def __init__(self, permission_name: str):
        super().__init__(f"Permission already exists: {permission_name}", "PERMISSION_EXISTS")


class PermissionAlreadyAssignedError(RBACException):
    """Raised when permission is already assigned to role."""
    
    def __init__(self, role_id: str, permission_id: str):
        super().__init__(
            f"Permission {permission_id} already assigned to role {role_id}",
            "PERMISSION_ALREADY_ASSIGNED"
        )


class RoleAlreadyAssignedError(RBACException):
    """Raised when role is already assigned to user."""
    
    def __init__(self, user_id: str, role_id: str):
        super().__init__(
            f"Role {role_id} already assigned to user {user_id}",
            "ROLE_ALREADY_ASSIGNED"
        )


class UserNotFoundError(RBACException):
    """Raised when user is not found."""
    
    def __init__(self, user_id: str):
        super().__init__(f"User not found: {user_id}", "USER_NOT_FOUND")


class SystemRoleError(RBACException):
    """Raised when trying to modify system role."""
    
    def __init__(self, role_name: str):
        super().__init__(
            f"Cannot modify system role: {role_name}",
            "SYSTEM_ROLE_ERROR"
        )


class PermissionDeniedError(RBACException):
    """Raised when user doesn't have required permission."""
    
    def __init__(self, user_id: str, resource: str, action: str):
        super().__init__(
            f"User {user_id} lacks permission: {resource}:{action}",
            "PERMISSION_DENIED"
        )


class RepositoryError(RBACException):
    """Raised when repository operation fails."""
    
    def __init__(self, message: str):
        super().__init__(message, "REPOSITORY_ERROR")


# ==================== PYDANTIC MODELS ====================

class RoleSchema(BaseModel):
    """Pydantic schema for role responses."""
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_system: bool


class PermissionSchema(BaseModel):
    """Pydantic schema for permission responses."""
    id: str
    name: str
    resource: str
    action: str
    description: Optional[str] = None
    created_at: datetime


class RoleWithPermissionsSchema(BaseModel):
    """Pydantic schema for role with permissions."""
    id: str
    name: str
    description: Optional[str] = None
    permissions: list[PermissionSchema] = []
    created_at: datetime


class UserPermissionsSchema(BaseModel):
    """Pydantic schema for user's permissions."""
    user_id: str
    roles: list[RoleSchema] = []
    permissions: list[PermissionSchema] = []