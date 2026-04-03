"""
Keycloak configuration module.

Reads and validates configuration from environment variables.
Supports OIDC, Admin API, and caching settings.
"""

import os
from typing import Optional
from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings


class KeycloakConfig(BaseSettings):
    """Keycloak configuration from environment variables."""

    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # ==================== OIDC Settings ====================
    oidc_issuer_url: str = Field(
        default="http://localhost:8080/realms/training-portal",
        description="Keycloak OIDC issuer URL"
    )
    
    oidc_client_id: str = Field(
        default="fastapi-backend",
        description="OIDC client ID (app client)"
    )
    
    oidc_audience: str = Field(
        default="fastapi-backend",
        description="OIDC audience claim to validate"
    )
    
    oidc_client_secret: Optional[str] = Field(
        default=None,
        description="OIDC client secret (if needed)"
    )
    
    oidc_redirect_uri: Optional[str] = Field(
        default="http://localhost:8000/auth/oidc/callback",
        description="OIDC redirect URI for OAuth2 flow"
    )

    # ==================== Keycloak Admin API ====================
    keycloak_admin_url: str = Field(
        default="http://localhost:8080",
        description="Keycloak server URL for Admin API"
    )
    
    keycloak_realm: str = Field(
        default="training-portal",
        description="Keycloak realm name"
    )
    
    keycloak_admin_client_id: str = Field(
        default="admin-cli",
        description="Admin API client ID"
    )
    
    keycloak_admin_username: str = Field(
        default="admin",
        description="Keycloak admin username"
    )
    
    keycloak_admin_password: str = Field(
        default="admin123",
        description="Keycloak admin password"
    )

    # ==================== Admin Portal Client ====================
    admin_client_id: Optional[str] = Field(
        default="admin-portal",
        description="Admin-only client ID (no OAuth2 broker shown)"
    )
    
    admin_client_secret: Optional[str] = Field(
        default=None,
        description="Admin client secret"
    )

    # ==================== JWKS Caching ====================
    jwks_cache_ttl: int = Field(
        default=600,
        description="JWKS cache time-to-live in seconds (default: 10 minutes)"
    )

    # ==================== Token Claims ====================
    role_claim: str = Field(
        default="realm_access.roles",
        description="JWT claim path to extract roles from (e.g., 'realm_access.roles')"
    )

    # ==================== Validation Settings ====================
    verify_signature: bool = Field(
        default=True,
        description="Verify JWT signature against JWKS"
    )
    
    verify_exp: bool = Field(
        default=True,
        description="Verify token expiration"
    )
    
    verify_aud: bool = Field(
        default=True,
        description="Verify audience claim"
    )

    # ==================== Computed Properties ====================
    @property
    def jwks_url(self) -> str:
        """Get JWKS endpoint URL."""
        return f"{self.oidc_issuer_url}/protocol/openid-connect/certs"

    @property
    def token_endpoint(self) -> str:
        """Get token endpoint URL."""
        return f"{self.oidc_issuer_url}/protocol/openid-connect/token"

    @property
    def userinfo_endpoint(self) -> str:
        """Get userinfo endpoint URL."""
        return f"{self.oidc_issuer_url}/protocol/openid-connect/userinfo"

    @property
    def admin_url(self) -> str:
        """Get admin API base URL."""
        return f"{self.keycloak_admin_url}/admin/realms/{self.keycloak_realm}"

    @property
    def admin_users_url(self) -> str:
        """Get admin users endpoint URL."""
        return f"{self.admin_url}/users"

    @property
    def admin_token_endpoint(self) -> str:
        """Get token endpoint for admin client."""
        return f"{self.keycloak_admin_url}/realms/{self.keycloak_realm}/protocol/openid-connect/token"


def get_keycloak_config() -> KeycloakConfig:
    """Get singleton Keycloak configuration instance."""
    return KeycloakConfig()