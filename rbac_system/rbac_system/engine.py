"""
RBAC Engine Module

Core RBAC logic for managing roles, permissions, and assignments.
Completely dynamic - no hard-coded roles or permissions.
"""

import logging
from typing import List, Optional

from rbac_system.models import (
    Role,
    Permission,
    RolePermissionAssignment,
    UserRoleAssignment,
    RoleNotFoundError,
    PermissionNotFoundError,
    RoleAlreadyExistsError,
    PermissionAlreadyExistsError,
    PermissionAlreadyAssignedError,
    RoleAlreadyAssignedError,
    SystemRoleError,
    PermissionDeniedError,
)

logger = logging.getLogger(__name__)


class RBACEngine:
    """
    Core RBAC (Role-Based Access Control) Engine.
    
    Manages creation and assignment of roles and permissions.
    Completely generic - no hard-coded roles or permissions.
    Uses repository pattern for data persistence.
    """

    def __init__(self, repository: "RBACRepository"):
        """
        Initialize RBAC Engine.
        
        Args:
            repository: RBAC data repository implementation
        """
        self.repository = repository
        logger.info("RBACEngine initialized")

    # ==================== ROLE MANAGEMENT ====================

    def create_role(self, name: str, description: str = "") -> Role:
        """
        Create a new role.
        
        Args:
            name: Role name (must be unique)
            description: Role description
            
        Returns:
            Created Role
            
        Raises:
            RoleAlreadyExistsError: If role with name already exists
        """
        logger.info(f"Creating role: {name}")
        
        # Check if role already exists
        try:
            existing = self.repository.get_role_by_name(name)
            if existing:
                raise RoleAlreadyExistsError(name)
        except RoleNotFoundError:
            pass  # Expected - role doesn't exist yet

        # Create role
        role = Role(name=name, description=description)
        saved_role = self.repository.save_role(role)
        logger.info(f"Role created: {saved_role.id}")
        return saved_role

    def delete_role(self, role_id: str) -> bool:
        """
        Delete a role.
        
        Args:
            role_id: Role ID
            
        Returns:
            True if deleted
            
        Raises:
            RoleNotFoundError: If role not found
            SystemRoleError: If role is system role
        """
        logger.info(f"Deleting role: {role_id}")
        
        role = self.repository.get_role(role_id)
        if role.is_system:
            raise SystemRoleError(role.name)
        
        self.repository.delete_role(role_id)
        logger.info(f"Role deleted: {role_id}")
        return True

    def get_role(self, role_id: str) -> Role:
        """Get role by ID."""
        return self.repository.get_role(role_id)

    def get_role_by_name(self, name: str) -> Role:
        """Get role by name."""
        return self.repository.get_role_by_name(name)

    def list_roles(self) -> List[Role]:
        """List all roles."""
        return self.repository.list_roles()

    # ==================== PERMISSION MANAGEMENT ====================

    def create_permission(
        self,
        resource: str,
        action: str,
        description: str = ""
    ) -> Permission:
        """
        Create a new permission.
        
        Args:
            resource: Resource name (e.g., "users", "tasks")
            action: Action name (e.g., "create", "approve")
            description: Permission description
            
        Returns:
            Created Permission
            
        Raises:
            PermissionAlreadyExistsError: If permission already exists
        """
        logger.info(f"Creating permission: {resource}:{action}")
        
        name = f"{resource}:{action}"
        
        # Check if permission already exists
        try:
            existing = self.repository.get_permission_by_name(name)
            if existing:
                raise PermissionAlreadyExistsError(name)
        except PermissionNotFoundError:
            pass  # Expected

        # Create permission
        permission = Permission(
            resource=resource,
            action=action,
            description=description
        )
        saved = self.repository.save_permission(permission)
        logger.info(f"Permission created: {saved.id}")
        return saved

    def delete_permission(self, permission_id: str) -> bool:
        """Delete a permission."""
        logger.info(f"Deleting permission: {permission_id}")
        self.repository.delete_permission(permission_id)
        logger.info(f"Permission deleted: {permission_id}")
        return True

    def get_permission(self, permission_id: str) -> Permission:
        """Get permission by ID."""
        return self.repository.get_permission(permission_id)

    def get_permission_by_name(self, name: str) -> Permission:
        """Get permission by name (resource:action)."""
        return self.repository.get_permission_by_name(name)

    def list_permissions(self) -> List[Permission]:
        """List all permissions."""
        return self.repository.list_permissions()

    # ==================== ROLE-PERMISSION ASSIGNMENTS ====================

    def assign_permission_to_role(
        self,
        role_id: str,
        permission_id: str
    ) -> bool:
        """
        Assign permission to role.
        
        Args:
            role_id: Role ID
            permission_id: Permission ID
            
        Returns:
            True if assigned
            
        Raises:
            PermissionAlreadyAssignedError: If already assigned
        """
        logger.info(f"Assigning permission {permission_id} to role {role_id}")
        
        # Check if already assigned
        try:
            existing = self.repository.get_role_permission_assignment(role_id, permission_id)
            if existing:
                raise PermissionAlreadyAssignedError(role_id, permission_id)
        except:
            pass  # Expected

        assignment = RolePermissionAssignment(
            role_id=role_id,
            permission_id=permission_id
        )
        self.repository.save_role_permission_assignment(assignment)
        logger.info(f"Permission assigned to role")
        return True

    def revoke_permission_from_role(
        self,
        role_id: str,
        permission_id: str
    ) -> bool:
        """Revoke permission from role."""
        logger.info(f"Revoking permission {permission_id} from role {role_id}")
        self.repository.delete_role_permission_assignment(role_id, permission_id)
        logger.info(f"Permission revoked from role")
        return True

    def get_role_permissions(self, role_id: str) -> List[Permission]:
        """Get all permissions for a role."""
        return self.repository.get_role_permissions(role_id)

    # ==================== USER-ROLE ASSIGNMENTS ====================

    def assign_role_to_user(
        self,
        user_id: str,
        role_id: str,
        assigned_by: Optional[str] = None
    ) -> bool:
        """
        Assign role to user.
        
        Args:
            user_id: User ID
            role_id: Role ID
            assigned_by: User ID who made the assignment (admin)
            
        Returns:
            True if assigned
            
        Raises:
            RoleAlreadyAssignedError: If already assigned
        """
        logger.info(f"Assigning role {role_id} to user {user_id}")
        
        # Check if already assigned
        try:
            existing = self.repository.get_user_role_assignment(user_id, role_id)
            if existing:
                raise RoleAlreadyAssignedError(user_id, role_id)
        except:
            pass  # Expected

        assignment = UserRoleAssignment(
            user_id=user_id,
            role_id=role_id,
            assigned_by=assigned_by
        )
        self.repository.save_user_role_assignment(assignment)
        logger.info(f"Role assigned to user")
        return True

    def revoke_role_from_user(self, user_id: str, role_id: str) -> bool:
        """Revoke role from user."""
        logger.info(f"Revoking role {role_id} from user {user_id}")
        self.repository.delete_user_role_assignment(user_id, role_id)
        logger.info(f"Role revoked from user")
        return True

    def get_user_roles(self, user_id: str) -> List[Role]:
        """Get all roles for a user."""
        return self.repository.get_user_roles(user_id)


class PermissionChecker:
    """
    Permission checking utility.
    
    Checks if users have specific permissions.
    Uses repository to fetch roles and permissions.
    """

    def __init__(self, repository: "RBACRepository"):
        """
        Initialize permission checker.
        
        Args:
            repository: RBAC data repository implementation
        """
        self.repository = repository
        logger.info("PermissionChecker initialized")

    def user_has_permission(
        self,
        user_id: str,
        resource: str,
        action: str
    ) -> bool:
        """
        Check if user has a specific permission.
        
        Args:
            user_id: User ID
            resource: Resource name
            action: Action name
            
        Returns:
            True if user has permission, False otherwise
        """
        logger.debug(f"Checking permission {resource}:{action} for user {user_id}")
        
        try:
            # Get user's roles
            roles = self.repository.get_user_roles(user_id)
            
            # Check each role for the permission
            for role in roles:
                permissions = self.repository.get_role_permissions(role.id)
                for perm in permissions:
                    if perm.resource == resource and perm.action == action:
                        logger.debug(f"User has permission: {resource}:{action}")
                        return True
            
            logger.debug(f"User lacks permission: {resource}:{action}")
            return False
            
        except Exception as e:
            logger.error(f"Error checking permission: {str(e)}")
            return False

    def user_has_role(self, user_id: str, role_name: str) -> bool:
        """Check if user has a specific role."""
        try:
            roles = self.repository.get_user_roles(user_id)
            return any(role.name == role_name for role in roles)
        except:
            return False

    def get_user_permissions(self, user_id: str) -> List[Permission]:
        """Get all permissions for a user."""
        permissions = []
        try:
            roles = self.repository.get_user_roles(user_id)
            for role in roles:
                role_perms = self.repository.get_role_permissions(role.id)
                permissions.extend(role_perms)
            # Remove duplicates
            return list({p.name: p for p in permissions}.values())
        except:
            return []

    def get_user_roles(self, user_id: str) -> List[Role]:
        """Get all roles for a user."""
        return self.repository.get_user_roles(user_id)