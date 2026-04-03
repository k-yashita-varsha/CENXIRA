"""
RBAC System Package

Generic, production-ready Role-Based Access Control (RBAC) engine.

No hard-coded roles or permissions - completely dynamic and reusable.
Uses repository pattern for flexible database implementations.

Example:
    from rbac_system.engine import RBACEngine, PermissionChecker
    from rbac_system.repository import RBACRepository
    
    engine = RBACEngine(your_db_repository)
    checker = PermissionChecker(your_db_repository)
    
    # Create role and permission
    admin_role = engine.create_role("admin", "Administrator")
    users_approve = engine.create_permission("users", "approve")
    
    # Assign permission to role
    engine.assign_permission_to_role(admin_role.id, users_approve.id)
    
    # Assign role to user
    engine.assign_role_to_user(user_id, admin_role.id)
    
    # Check permission
    if checker.user_has_permission(user_id, "users", "approve"):
        # User can approve users
        pass
"""

__version__ = "1.0.0"
__author__ = "Training Portal Team"

from rbac_system.config import RBACConfig
from rbac_system.models import (
    Role,
    Permission,
    RolePermissionAssignment,
    UserRoleAssignment,
)
from rbac_system.engine import RBACEngine, PermissionChecker
from rbac_system.repository import RBACRepository
from rbac_system.fastapi_utils import require_permission, require_role

__all__ = [
    "RBACConfig",
    "Role",
    "Permission",
    "RolePermissionAssignment",
    "UserRoleAssignment",
    "RBACEngine",
    "PermissionChecker",
    "RBACRepository",
    "require_permission",
    "require_role",
]