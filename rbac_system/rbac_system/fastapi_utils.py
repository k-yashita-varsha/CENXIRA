"""
FastAPI Utilities for RBAC

Provides FastAPI dependencies and guards for role and permission checking.
"""

import logging
from typing import Optional, Any, List, Union
from fastapi import HTTPException, status, Depends

from rbac_system.config import RBACConfig
from rbac_system.engine import PermissionChecker

logger = logging.getLogger(__name__)

# Global instances (lazy loaded)
_config: Optional[RBACConfig] = None
_permission_checker: Optional[PermissionChecker] = None


def get_config() -> RBACConfig:
    """
    Get or create RBAC configuration (singleton).
    
    Returns:
        RBACConfig instance
    """
    global _config
    if _config is None:
        _config = RBACConfig()
        logger.info("RBAC config initialized")
    return _config


def set_permission_checker(checker: PermissionChecker) -> None:
    """
    Set the permission checker instance.
    
    Must be called during application startup with
    your repository implementation.
    
    Args:
        checker: PermissionChecker instance with your repository
    """
    global _permission_checker
    _permission_checker = checker
    logger.info("Permission checker set")


def get_permission_checker() -> PermissionChecker:
    """
    Get permission checker instance.
    
    Must be set via set_permission_checker() during startup.
    
    Returns:
        PermissionChecker instance
        
    Raises:
        RuntimeError: If not initialized
    """
    if _permission_checker is None:
        raise RuntimeError(
            "Permission checker not initialized. "
            "Call set_permission_checker() during app startup."
        )
    return _permission_checker


def require_permission(resource: str, action: str):
    """
    FastAPI dependency to check user has specific permission.
    
    Returns the user object if successful.
    """
    from keycloak_auth.fastapi_utils import get_current_user
    
    async def dependency(user: Optional[Any] = Depends(get_current_user)):
        """Check permission for authenticated user."""
        if not user:
            logger.warning(f"No user provided for permission check {resource}:{action}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        try:
            checker = get_permission_checker()
            has_permission = checker.user_has_permission(
                user.user_id,
                resource,
                action
            )

            if not has_permission:
                logger.warning(
                    f"User {user.user_id} denied permission: {resource}:{action}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {resource}:{action}",
                )

            logger.debug(f"User {user.user_id} granted {resource}:{action}")
            return user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error checking permission: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Permission check failed",
            )

    return dependency


# Global Role Provider (optional backup check)
_role_provider: Optional[Any] = None

def set_role_provider(provider_func: Any) -> None:
    """Set a backup role provider function (e.g. to check a local DB)."""
    global _role_provider
    _role_provider = provider_func

def require_role(role_name: Union[str, List[str]]):
    """
    FastAPI dependency to check user has specific role(s).
    Checks Token (Fast) and Provider/DB (Backup).
    """
    from keycloak_auth.fastapi_utils import get_current_user
    
    if isinstance(role_name, str):
        required_roles = [role_name.lower()]
        display_name = role_name
    else:
        required_roles = [r.lower() for r in role_name]
        display_name = ", ".join(role_name)
    
    async def dependency(user: Optional[Any] = Depends(get_current_user)):
        """Check role for authenticated user (checks Token + Backup Provider)."""
        if not user:
            logger.warning(f"No user provided for role check: {display_name}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        try:
            # 1. Fast path: Check JWT token roles
            user_roles_lower = [r.lower() for r in user.roles]
            has_role = any(r in user_roles_lower for r in required_roles)

            # 2. Backup path: Dynamic Provider (e.g. check local Database)
            if not has_role and _role_provider:
                has_role = await _role_provider(user.user_id, required_roles)

            if not has_role:
                logger.warning(f"User {user.user_id} missing role: {display_name}. Token roles: {user.roles}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access Denied: {display_name} role required.",
                )

            return user
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error checking role: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Role check failed",
            )

    return dependency