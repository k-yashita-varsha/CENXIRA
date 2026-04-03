"""
Data models for Keycloak authentication.

Contains Pydantic models for token claims and authenticated user information.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class TokenClaims(BaseModel):
    """
    JWT token claims extracted from Keycloak OIDC token.
    
    These are the raw claims from the JWT payload.
    """

    sub: str = Field(..., description="Subject (user ID)")
    email: Optional[str] = Field(None, description="User email")
    email_verified: Optional[bool] = Field(None, description="Email verified flag")
    name: Optional[str] = Field(None, description="Full name")
    given_name: Optional[str] = Field(None, description="First name")
    family_name: Optional[str] = Field(None, description="Last name")
    preferred_username: str = Field(..., description="Username")
    
    # Timing
    exp: int = Field(..., description="Token expiration timestamp")
    iat: int = Field(..., description="Token issued at timestamp")
    nbf: Optional[int] = Field(None, description="Not before timestamp")
    
    # OIDC Claims
    iss: Optional[str] = Field(None, description="Token issuer")
    aud: Optional[Any] = Field(None, description="Audience (can be string or list)")
    jti: Optional[str] = Field(None, description="JWT ID")
    typ: Optional[str] = Field(None, description="Token type")
    
    # Keycloak-specific
    acr: Optional[str] = Field(None, description="Authentication context class")
    nonce: Optional[str] = Field(None, description="Nonce")
    
    # Roles and Access (from realm_access.roles)
    roles: List[str] = Field(default_factory=list, description="Realm roles")
    
    # Custom attributes (from attributes claim)
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Custom attributes")
    
    # Raw token payload
    raw_payload: Dict[str, Any] = Field(default_factory=dict, description="Full token payload")

    class Config:
        """Pydantic config."""
        populate_by_name = True

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.now().timestamp() > self.exp

    @property
    def expires_at(self) -> datetime:
        """Get token expiration as datetime."""
        return datetime.fromtimestamp(self.exp)

    @property
    def issued_at(self) -> datetime:
        """Get token issued time as datetime."""
        return datetime.fromtimestamp(self.iat)


class AuthenticatedUser(BaseModel):
    """
    Authenticated user information.
    
    This is the model returned to FastAPI routes after token validation.
    Contains parsed and validated user information ready for use.
    """

    # User Identity
    user_id: str = Field(..., description="Unique user ID (from 'sub' claim)")
    username: str = Field(..., description="Username (from 'preferred_username')")
    email: Optional[str] = Field(None, description="Email address")
    
    # Name Information
    full_name: Optional[str] = Field(None, description="Full name")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    
    # Authorization
    roles: List[str] = Field(default_factory=list, description="User roles from token")
    
    # Custom Attributes
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Custom user attributes")
    
    # Token Information
    token_exp: int = Field(..., description="Token expiration timestamp")
    token_issued_at: int = Field(..., description="Token issued at timestamp")
    
    # Status
    is_active: bool = Field(default=True, description="User account active status")
    email_verified: bool = Field(default=False, description="Email verification status")

    @property
    def id(self) -> str:
        """Alias for user_id to maintain backward compatibility."""
        return self.user_id

    class Config:
        """Pydantic config."""
        from_attributes = True

    @property
    def status(self) -> Optional[str]:
        """Get user status from attributes (ACTIVE, PENDING, INACTIVE, REJECTED)."""
        return self.attributes.get("status")

    @property
    def ohr_id(self) -> Optional[str]:
        """Get OHR ID from attributes (company email)."""
        return self.attributes.get("ohr_id")

    @property
    def expires_at(self) -> datetime:
        """Get token expiration as datetime."""
        return datetime.fromtimestamp(self.token_exp)

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.now().timestamp() > self.token_exp

    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role."""
        return role_name in self.roles

    def has_any_role(self, role_names: List[str]) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in self.roles for role in role_names)

    def has_all_roles(self, role_names: List[str]) -> bool:
        """Check if user has all of the specified roles."""
        return all(role in self.roles for role in role_names)