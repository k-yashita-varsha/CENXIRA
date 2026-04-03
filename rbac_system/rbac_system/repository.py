"""
RBAC Repository Module

Abstract repository interface for RBAC data operations.
Implementations can use any database (SQL, NoSQL, etc).
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from rbac_system.models import (
    Role,
    Permission,
    RolePermissionAssignment,
    UserRoleAssignment,
    RoleNotFoundError,
    PermissionNotFoundError,
    RepositoryError,
)


class RBACRepository(ABC):
    """
    Abstract RBAC Repository.
    
    Defines interface for RBAC data operations.
    Implement this interface with your database technology.
    
    Example implementations:
    - SQLAlchemyRBACRepository (PostgreSQL, MySQL, SQLite)
    - MongoDBRBACRepository
    - FirestoreRBACRepository
    """

    # ==================== ROLE OPERATIONS ====================

    @abstractmethod
    def save_role(self, role: Role) -> Role:
        """Save a role to database."""
        pass

    @abstractmethod
    def get_role(self, role_id: str) -> Role:
        """Get role by ID. Raise RoleNotFoundError if not found."""
        pass

    @abstractmethod
    def get_role_by_name(self, name: str) -> Role:
        """Get role by name. Raise RoleNotFoundError if not found."""
        pass

    @abstractmethod
    def delete_role(self, role_id: str) -> bool:
        """Delete role."""
        pass

    @abstractmethod
    def list_roles(self) -> List[Role]:
        """List all roles."""
        pass

    # ==================== PERMISSION OPERATIONS ====================

    @abstractmethod
    def save_permission(self, permission: Permission) -> Permission:
        """Save a permission to database."""
        pass

    @abstractmethod
    def get_permission(self, permission_id: str) -> Permission:
        """Get permission by ID. Raise PermissionNotFoundError if not found."""
        pass

    @abstractmethod
    def get_permission_by_name(self, name: str) -> Permission:
        """Get permission by name (resource:action). Raise PermissionNotFoundError if not found."""
        pass

    @abstractmethod
    def delete_permission(self, permission_id: str) -> bool:
        """Delete permission."""
        pass

    @abstractmethod
    def list_permissions(self) -> List[Permission]:
        """List all permissions."""
        pass

    # ==================== ROLE-PERMISSION ASSIGNMENTS ====================

    @abstractmethod
    def save_role_permission_assignment(
        self,
        assignment: RolePermissionAssignment
    ) -> RolePermissionAssignment:
        """Save role-permission assignment."""
        pass

    @abstractmethod
    def get_role_permission_assignment(
        self,
        role_id: str,
        permission_id: str
    ) -> Optional[RolePermissionAssignment]:
        """Get role-permission assignment."""
        pass

    @abstractmethod
    def delete_role_permission_assignment(
        self,
        role_id: str,
        permission_id: str
    ) -> bool:
        """Delete role-permission assignment."""
        pass

    @abstractmethod
    def get_role_permissions(self, role_id: str) -> List[Permission]:
        """Get all permissions for a role."""
        pass

    # ==================== USER-ROLE ASSIGNMENTS ====================

    @abstractmethod
    def save_user_role_assignment(
        self,
        assignment: UserRoleAssignment
    ) -> UserRoleAssignment:
        """Save user-role assignment."""
        pass

    @abstractmethod
    def get_user_role_assignment(
        self,
        user_id: str,
        role_id: str
    ) -> Optional[UserRoleAssignment]:
        """Get user-role assignment."""
        pass

    @abstractmethod
    def delete_user_role_assignment(
        self,
        user_id: str,
        role_id: str
    ) -> bool:
        """Delete user-role assignment."""
        pass

    @abstractmethod
    def get_user_roles(self, user_id: str) -> List[Role]:
        """Get all roles for a user."""
        pass


from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from rbac_system.models import (
    Role as RoleModel,
    Permission as PermissionModel,
    RolePermissionAssignment as RolePermissionAssignmentModel,
    UserRoleAssignment as UserRoleAssignmentModel
)

class SQLAlchemyRBACRepository(RBACRepository):
    """
    SQLAlchemy implementation of RBAC Repository.
    """

    def __init__(self, engine):
        """Initialize with SQLAlchemy engine."""
        self.engine = engine

    def _get_session(self):
        """Helper to get a synchronous session from the engine."""
        return Session(self.engine)

    def save_role(self, role: RoleModel) -> RoleModel:
        with self._get_session() as session:
            session.add(role)
            session.commit()
            session.refresh(role)
            return role

    def get_role(self, role_id: str) -> RoleModel:
        with self._get_session() as session:
            role = session.get(RoleModel, role_id)
            if not role:
                from rbac_system.models import RoleNotFoundError
                raise RoleNotFoundError(role_id)
            return role

    def get_role_by_name(self, name: str) -> RoleModel:
        with self._get_session() as session:
            stmt = select(RoleModel).where(RoleModel.name == name)
            role = session.execute(stmt).scalar_one_or_none()
            if not role:
                from rbac_system.models import RoleNotFoundError
                raise RoleNotFoundError(name)
            return role

    def delete_role(self, role_id: str) -> bool:
        with self._get_session() as session:
            stmt = delete(RoleModel).where(RoleModel.id == role_id)
            result = session.execute(stmt)
            session.commit()
            return result.rowcount > 0

    def list_roles(self) -> List[RoleModel]:
        with self._get_session() as session:
            stmt = select(RoleModel)
            return list(session.execute(stmt).scalars().all())

    def save_permission(self, permission: PermissionModel) -> PermissionModel:
        with self._get_session() as session:
            session.add(permission)
            session.commit()
            session.refresh(permission)
            return permission

    def get_permission(self, permission_id: str) -> PermissionModel:
        with self._get_session() as session:
            perm = session.get(PermissionModel, permission_id)
            if not perm:
                from rbac_system.models import PermissionNotFoundError
                raise PermissionNotFoundError(permission_id)
            return perm

    def get_permission_by_name(self, name: str) -> PermissionModel:
        with self._get_session() as session:
            stmt = select(PermissionModel).where(PermissionModel.name == name)
            perm = session.execute(stmt).scalar_one_or_none()
            if not perm:
                from rbac_system.models import PermissionNotFoundError
                raise PermissionNotFoundError(name)
            return perm

    def delete_permission(self, permission_id: str) -> bool:
        with self._get_session() as session:
            stmt = delete(PermissionModel).where(PermissionModel.id == permission_id)
            result = session.execute(stmt)
            session.commit()
            return result.rowcount > 0

    def list_permissions(self) -> List[PermissionModel]:
        with self._get_session() as session:
            stmt = select(PermissionModel)
            return list(session.execute(stmt).scalars().all())

    def save_role_permission_assignment(
        self,
        assignment: RolePermissionAssignmentModel
    ) -> RolePermissionAssignmentModel:
        with self._get_session() as session:
            session.add(assignment)
            session.commit()
            session.refresh(assignment)
            return assignment

    def get_role_permission_assignment(
        self,
        role_id: str,
        permission_id: str
    ) -> Optional[RolePermissionAssignmentModel]:
        with self._get_session() as session:
            stmt = select(RolePermissionAssignmentModel).where(
                RolePermissionAssignmentModel.role_id == role_id,
                RolePermissionAssignmentModel.permission_id == permission_id
            )
            return session.execute(stmt).scalar_one_or_none()

    def delete_role_permission_assignment(
        self,
        role_id: str,
        permission_id: str
    ) -> bool:
        with self._get_session() as session:
            stmt = delete(RolePermissionAssignmentModel).where(
                RolePermissionAssignmentModel.role_id == role_id,
                RolePermissionAssignmentModel.permission_id == permission_id
            )
            result = session.execute(stmt)
            session.commit()
            return result.rowcount > 0

    def get_role_permissions(self, role_id: str) -> List[PermissionModel]:
        with self._get_session() as session:
            stmt = select(PermissionModel).join(
                RolePermissionAssignmentModel,
                PermissionModel.id == RolePermissionAssignmentModel.permission_id
            ).where(RolePermissionAssignmentModel.role_id == role_id)
            return list(session.execute(stmt).scalars().all())

    def save_user_role_assignment(
        self,
        assignment: UserRoleAssignmentModel
    ) -> UserRoleAssignmentModel:
        with self._get_session() as session:
            session.add(assignment)
            session.commit()
            session.refresh(assignment)
            return assignment

    def get_user_role_assignment(
        self,
        user_id: str,
        role_id: str
    ) -> Optional[UserRoleAssignmentModel]:
        with self._get_session() as session:
            stmt = select(UserRoleAssignmentModel).where(
                UserRoleAssignmentModel.user_id == user_id,
                UserRoleAssignmentModel.role_id == role_id
            )
            return session.execute(stmt).scalar_one_or_none()

    def delete_user_role_assignment(
        self,
        user_id: str,
        role_id: str
    ) -> bool:
        with self._get_session() as session:
            stmt = delete(UserRoleAssignmentModel).where(
                UserRoleAssignmentModel.user_id == user_id,
                UserRoleAssignmentModel.role_id == role_id
            )
            result = session.execute(stmt)
            session.commit()
            return result.rowcount > 0

    def get_user_roles(self, user_id: str) -> List[RoleModel]:
        with self._get_session() as session:
            stmt = select(RoleModel).join(
                UserRoleAssignmentModel,
                RoleModel.id == UserRoleAssignmentModel.role_id
            ).where(UserRoleAssignmentModel.user_id == user_id)
            return list(session.execute(stmt).scalars().all())