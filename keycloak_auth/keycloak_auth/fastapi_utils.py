"""
FastAPI utilities for Keycloak authentication.

Provides Depends() functions for FastAPI route protection and authentication.
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

# Import HTTPAuthenticationCredentials - compatible with all FastAPI versions
try:
    from fastapi.security import HTTPAuthenticationCredentials
except ImportError:
    # Fallback for newer FastAPI versions
    class HTTPAuthenticationCredentials:
        def __init__(self, scheme: str, credentials: str):
            self.scheme = scheme
            self.credentials = credentials

from keycloak_auth.config import get_keycloak_config, KeycloakConfig
from keycloak_auth.core import (
    TokenValidator,
    TokenParser,
    TokenExpiredError,
    InvalidSignatureError,
    TokenValidationError,
    KeycloakAuthException,
)
from keycloak_auth.models import AuthenticatedUser

logger = logging.getLogger(__name__)

# Global instances (lazy loaded)
_security_scheme = HTTPBearer(auto_error=False)
_token_validator: Optional[TokenValidator] = None


def get_token_validator() -> TokenValidator:
    """Get or create token validator singleton."""
    global _token_validator
    if _token_validator is None:
        config = get_keycloak_config()
        _token_validator = TokenValidator(config)
    return _token_validator


async def get_current_user(
    credentials: Optional[HTTPAuthenticationCredentials] = Depends(_security_scheme),
) -> AuthenticatedUser:
    """
    FastAPI dependency to get current authenticated user.
    
    Validates JWT token against Keycloak OIDC and returns authenticated user.
    
    Use in routes:
        @app.get("/api/me")
        async def get_me(user = Depends(get_current_user)):
            return {"user_id": user.user_id}
    
    Args:
        credentials: HTTP Bearer token from Authorization header
        
    Returns:
        AuthenticatedUser with parsed token claims
        
    Raises:
        HTTPException: 401 if not authenticated, 503 if service error
    """
    if not credentials:
        logger.warning("No credentials provided in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        validator = get_token_validator()
        claims = validator.validate_token(token)
        user = TokenParser.to_authenticated_user(claims)
        logger.debug(f"User authenticated: {user.user_id}")
        return user

    except TokenExpiredError as e:
        logger.warning(f"Token expired: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidSignatureError as e:
        logger.warning(f"Invalid signature: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except TokenValidationError as e:
        logger.warning(f"Token validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except KeycloakAuthException as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service error",
        )
    except Exception as e:
        logger.error(f"Unexpected error during authentication: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


async def get_current_active_user(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """
    FastAPI dependency to get current active user.
    
    Validates that user is authenticated AND has status = ACTIVE.
    
    Use in routes that require active users:
        @app.get("/api/training")
        async def training(user = Depends(get_current_active_user)):
            return {"user": user.username}
    
    Args:
        user: Current authenticated user from get_current_user
        
    Returns:
        AuthenticatedUser if active
        
    Raises:
        HTTPException: 403 if user is not active
    """
    if not user.is_active:
        status_attr = user.status or "UNKNOWN"
        logger.warning(
            f"Inactive user attempted access: {user.user_id} (status: {status_attr})"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User account is not active (status: {status_attr})",
        )

    return user


async def get_current_user_or_none(
    credentials: Optional[HTTPAuthenticationCredentials] = Depends(_security_scheme),
) -> Optional[AuthenticatedUser]:
    """
    FastAPI dependency to get current user or None.
    
    Similar to get_current_user but doesn't raise exception if not authenticated.
    Returns None if no valid token provided.
    
    Useful for routes that can serve both authenticated and unauthenticated users:
        @app.get("/api/public")
        async def public_route(user = Depends(get_current_user_or_none)):
            if user:
                return {"message": f"Hello {user.username}"}
            else:
                return {"message": "Hello guest"}
    
    Args:
        credentials: HTTP Bearer token from Authorization header
        
    Returns:
        AuthenticatedUser if valid token, None otherwise
    """
    if not credentials:
        logger.debug("No credentials provided, returning None")
        return None

    token = credentials.credentials

    try:
        validator = get_token_validator()
        claims = validator.validate_token(token)
        user = TokenParser.to_authenticated_user(claims)
        logger.debug(f"User authenticated: {user.user_id}")
        return user

    except KeycloakAuthException as e:
        logger.debug(f"Authentication failed (returning None): {str(e)}")
        return None
    except Exception as e:
        logger.debug(f"Unexpected error (returning None): {str(e)}")
        return None