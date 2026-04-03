"""
Keycloak Authentication Package

OIDC JWT validation from Keycloak with JWKS caching and Admin API integration.
"""

__version__ = "1.0.0"
__author__ = "Training Portal Team"

from keycloak_auth.models import TokenClaims, AuthenticatedUser
from keycloak_auth.core import TokenValidator, TokenParser, TokenExchanger
from keycloak_auth.admin import KeycloakAdminClient
from keycloak_auth.fastapi_utils import (
    get_current_user,
    get_current_active_user,
    get_current_user_or_none,
)

__all__ = [
    "TokenClaims",
    "AuthenticatedUser",
    "TokenValidator",
    "TokenParser",
    "TokenExchanger",
    "KeycloakAdminClient",
    "get_current_user",
    "get_current_active_user",
    "get_current_user_or_none",
]