"""
Core Keycloak authentication module.

Handles JWT token validation, JWKS caching, token parsing, and exception definitions.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import jwt
import requests

from keycloak_auth.config import KeycloakConfig
from keycloak_auth.models import TokenClaims, AuthenticatedUser

logger = logging.getLogger(__name__)


# ==================== EXCEPTIONS ====================

class KeycloakAuthException(Exception):
    """Base exception for Keycloak authentication errors."""

    def __init__(self, message: str, code: str = "AUTH_ERROR"):
        """Initialize exception."""
        self.message = message
        self.code = code
        super().__init__(self.message)


class TokenValidationError(KeycloakAuthException):
    """Raised when token validation fails."""

    def __init__(self, message: str):
        super().__init__(message, "TOKEN_INVALID")


class TokenExpiredError(KeycloakAuthException):
    """Raised when token is expired."""

    def __init__(self, message: str = "Token has expired"):
        super().__init__(message, "TOKEN_EXPIRED")


class InvalidSignatureError(KeycloakAuthException):
    """Raised when token signature is invalid."""

    def __init__(self, message: str = "Invalid token signature"):
        super().__init__(message, "INVALID_SIGNATURE")


class JWKSError(KeycloakAuthException):
    """Raised when JWKS retrieval or parsing fails."""

    def __init__(self, message: str):
        super().__init__(message, "JWKS_ERROR")


class KeycloakConnectionError(KeycloakAuthException):
    """Raised when connection to Keycloak fails."""

    def __init__(self, message: str):
        super().__init__(message, "KEYCLOAK_CONNECTION_ERROR")


class UserNotFoundError(KeycloakAuthException):
    """Raised when user is not found in Keycloak."""

    def __init__(self, message: str = "User not found"):
        super().__init__(message, "USER_NOT_FOUND")


class AdminAPIError(KeycloakAuthException):
    """Raised when Keycloak Admin API call fails."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message, "ADMIN_API_ERROR")
        self.status_code = status_code


class MissingClaimError(KeycloakAuthException):
    """Raised when required claim is missing from token."""

    def __init__(self, claim_name: str):
        message = f"Required claim '{claim_name}' not found in token"
        super().__init__(message, "MISSING_CLAIM")


class InvalidAudienceError(KeycloakAuthException):
    """Raised when token audience doesn't match expected audience."""

    def __init__(self, message: str = "Invalid token audience"):
        super().__init__(message, "INVALID_AUDIENCE")


# ==================== JWKS CACHE ====================

class JWKSCache:
    """
    JWKS (JSON Web Key Set) cache with TTL.
    
    Caches public keys from Keycloak to avoid repeated requests.
    Automatically expires after configured TTL.
    """

    def __init__(self, ttl_seconds: int = 600):
        """
        Initialize JWKS cache.
        
        Args:
            ttl_seconds: Cache time-to-live in seconds
        """
        self.ttl_seconds = ttl_seconds
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_expires_at: Optional[datetime] = None
        logger.debug(f"JWKSCache initialized with TTL: {ttl_seconds}s")

    def is_expired(self) -> bool:
        """Check if cache is expired."""
        if self._cache is None or self._cache_expires_at is None:
            return True
        return datetime.now() >= self._cache_expires_at

    def get(self) -> Optional[Dict[str, Any]]:
        """Get cached JWKS if not expired."""
        if not self.is_expired():
            logger.debug("Using cached JWKS")
            return self._cache
        return None

    def set(self, jwks: Dict[str, Any]) -> None:
        """
        Set cache with new JWKS.
        
        Args:
            jwks: JWKS dictionary from Keycloak
        """
        self._cache = jwks
        self._cache_expires_at = datetime.now() + timedelta(seconds=self.ttl_seconds)
        logger.info(
            f"JWKS cached with {len(jwks.get('keys', []))} keys, "
            f"expires at {self._cache_expires_at}"
        )

    def clear(self) -> None:
        """Clear cache."""
        self._cache = None
        self._cache_expires_at = None
        logger.debug("JWKS cache cleared")


# ==================== TOKEN VALIDATOR ====================

class TokenValidator:
    """
    Validates JWT tokens from Keycloak OIDC.
    
    Handles:
    - JWKS key fetching and caching
    - JWT signature verification (RS256)
    - Token expiration checking
    - Audience validation
    - Token claim extraction
    """

    def __init__(self, config: KeycloakConfig):
        """
        Initialize token validator.
        
        Args:
            config: Keycloak configuration
        """
        self.config = config
        self.jwks_cache = JWKSCache(ttl_seconds=config.jwks_cache_ttl)
        logger.info(
            f"TokenValidator initialized for realm: {config.keycloak_realm} "
            f"at {config.oidc_issuer_url}"
        )

    def get_jwks(self) -> Dict[str, Any]:
        """
        Get JWKS from cache or fetch from Keycloak.
        
        Returns:
            JWKS dictionary with public keys
            
        Raises:
            JWKSError: If JWKS retrieval fails
            KeycloakConnectionError: If connection to Keycloak fails
        """
        # Check cache first
        cached_jwks = self.jwks_cache.get()
        if cached_jwks is not None:
            return cached_jwks

        # Fetch from Keycloak
        try:
            logger.info(f"Fetching JWKS from {self.config.jwks_url}")
            response = requests.get(self.config.jwks_url, timeout=10)
            response.raise_for_status()
            jwks = response.json()

            if "keys" not in jwks or not jwks["keys"]:
                raise JWKSError("JWKS response missing 'keys' array")

            self.jwks_cache.set(jwks)
            return jwks

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to Keycloak: {str(e)}")
            raise KeycloakConnectionError(f"Failed to connect to Keycloak: {str(e)}")
        except requests.exceptions.Timeout as e:
            logger.error(f"Keycloak connection timeout: {str(e)}")
            raise KeycloakConnectionError(f"Keycloak connection timeout: {str(e)}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch JWKS: {str(e)}")
            raise JWKSError(f"Failed to fetch JWKS: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in JWKS response: {str(e)}")
            raise JWKSError(f"Invalid JSON in JWKS response: {str(e)}")

    def get_kid_from_token_header(self, token: str) -> str:
        """
        Extract 'kid' (key ID) from JWT header.
        
        Args:
            token: JWT token string
            
        Returns:
            Key ID from token header
            
        Raises:
            TokenValidationError: If token header is invalid
        """
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if not kid:
                raise TokenValidationError("Token header missing 'kid' claim")
            return kid
        except jwt.DecodeError as e:
            raise TokenValidationError(f"Failed to decode token header: {str(e)}")
        except Exception as e:
            raise TokenValidationError(f"Error extracting kid from token: {str(e)}")

    def get_public_key(self, kid: str, jwks: Dict[str, Any]) -> Any:
        """
        Get public key from JWKS by key ID.
        
        Args:
            kid: Key ID to look up
            jwks: JWKS dictionary from Keycloak
            
        Returns:
            Public key for RSA verification
            
        Raises:
            TokenValidationError: If key not found in JWKS
        """
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                try:
                    from jwt.algorithms import RSAAlgorithm
                    return RSAAlgorithm.from_jwk(json.dumps(key))
                except Exception as e:
                    logger.error(f"Failed to construct public key: {str(e)}")
                    raise TokenValidationError(f"Invalid key in JWKS: {str(e)}")

        logger.warning(f"Key with kid '{kid}' not found in JWKS")
        raise TokenValidationError(f"Key with ID '{kid}' not found in JWKS")

    def validate_token(self, token: str) -> TokenClaims:
        """
        Validate JWT token and return claims.
        
        Validates signature, expiration, and audience.
        
        Args:
            token: JWT token string
            
        Returns:
            TokenClaims with extracted token claims
            
        Raises:
            TokenExpiredError: If token is expired
            InvalidSignatureError: If signature is invalid
            InvalidAudienceError: If audience doesn't match
            TokenValidationError: If token is invalid for any reason
            JWKSError: If JWKS retrieval fails
        """
        logger.debug("Starting token validation")

        # Get token header and extract kid
        try:
            kid = self.get_kid_from_token_header(token)
        except TokenValidationError as e:
            logger.warning(f"Failed to get kid from token: {str(e)}")
            raise

        # Get JWKS and public key
        try:
            jwks = self.get_jwks()
            public_key = self.get_public_key(kid, jwks)
        except (JWKSError, KeycloakConnectionError, TokenValidationError) as e:
            logger.error(f"Failed to get public key: {str(e)}")
            raise

        # Verify and decode token
        try:
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                options={
                    "verify_signature": self.config.verify_signature,
                    "verify_exp": self.config.verify_exp,
                    "verify_aud": self.config.verify_aud,
                },
                audience=self.config.oidc_audience if self.config.verify_aud else None,
            )
            logger.debug("Token signature verified successfully")

        except jwt.ExpiredSignatureError as e:
            logger.warning(f"Token expired: {str(e)}")
            raise TokenExpiredError(f"Token has expired: {str(e)}")
        except jwt.InvalidSignatureError as e:
            logger.warning(f"Invalid token signature: {str(e)}")
            raise InvalidSignatureError(f"Invalid token signature: {str(e)}")
        except jwt.InvalidAudienceError as e:
            logger.warning(f"Invalid token audience: {str(e)}")
            raise InvalidAudienceError(f"Invalid token audience: {str(e)}")
        except jwt.DecodeError as e:
            logger.warning(f"Failed to decode token: {str(e)}")
            raise TokenValidationError(f"Failed to decode token: {str(e)}")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            raise TokenValidationError(f"Invalid token: {str(e)}")

        # Parse claims
        try:
            claims = TokenClaims(
                sub=payload.get("sub"),
                email=payload.get("email"),
                email_verified=payload.get("email_verified"),
                name=payload.get("name"),
                given_name=payload.get("given_name"),
                family_name=payload.get("family_name"),
                preferred_username=payload.get("preferred_username"),
                exp=payload.get("exp"),
                iat=payload.get("iat"),
                nbf=payload.get("nbf"),
                iss=payload.get("iss"),
                aud=payload.get("aud"),
                jti=payload.get("jti"),
                typ=payload.get("typ"),
                acr=payload.get("acr"),
                nonce=payload.get("nonce"),
                roles=self._extract_roles(payload),
                attributes=payload.get("attributes", {}),
                raw_payload=payload,
            )
            logger.info(f"Token validated for user: {claims.sub}")
            return claims

        except Exception as e:
            logger.error(f"Failed to parse token claims: {str(e)}")
            raise TokenValidationError(f"Failed to parse token claims: {str(e)}")

    def _extract_roles(self, payload: Dict[str, Any]) -> list:
        """
        Extract roles from token payload using configured claim path and client access.
        
        Args:
            payload: JWT payload
            
        Returns:
            List of roles combined from realm and client access.
        """
        roles = set()
        try:
            # 1. Extract from configured claim path (usually realm_access.roles)
            claim_parts = self.config.role_claim.split(".")
            value = payload
            for part in claim_parts:
                if isinstance(value, dict):
                    value = value.get(part, {})
                else:
                    value = None
                    break
            
            if isinstance(value, list):
                roles.update(value)

            # 2. Automatically extract from resource_access (Client Roles)
            # This handles cases where roles are mapped to the client specifically
            client_id = self.config.oidc_client_id
            if client_id:
                client_access = payload.get("resource_access", {}).get(client_id, {})
                client_roles = client_access.get("roles", [])
                if isinstance(client_roles, list):
                    roles.update(client_roles)
            
            # Special case for 'aud' if it contains client id (sometimes roles are there)
            # but usually 'resource_access' is the standard place.

            return list(roles)
        except Exception as e:
            logger.warning(f"Failed to extract roles from token: {e}")
            return list(roles)

    def refresh_jwks_cache(self) -> Dict[str, Any]:
        """
        Force refresh of JWKS cache.
        
        Useful when JWKS may have changed (e.g., after key rotation).
        
        Returns:
            Fresh JWKS from Keycloak
        """
        logger.info("Forcing JWKS cache refresh")
        self.jwks_cache.clear()
        return self.get_jwks()


# ==================== TOKEN PARSER ====================

class TokenParser:
    """
    Parses token claims and extracts user information.
    
    Converts TokenClaims (raw JWT claims) into AuthenticatedUser
    (application-specific user model ready for FastAPI routes).
    """

    @staticmethod
    def to_authenticated_user(claims: TokenClaims) -> AuthenticatedUser:
        """
        Convert TokenClaims to AuthenticatedUser.
        
        Args:
            claims: Token claims from validator
            
        Returns:
            AuthenticatedUser instance
        """
        return AuthenticatedUser(
            user_id=claims.sub,
            username=claims.preferred_username,
            email=claims.email,
            full_name=claims.name,
            first_name=claims.given_name,
            last_name=claims.family_name,
            roles=claims.roles,
            attributes=claims.attributes,
            token_exp=claims.exp,
            token_issued_at=claims.iat,
            is_active=claims.attributes.get("status") != "INACTIVE",
            email_verified=claims.email_verified or False,
        )

    @staticmethod
    def extract_user_id(claims: TokenClaims) -> str:
        """Extract user ID from claims."""
        if not claims.sub:
            raise MissingClaimError("sub")
        return claims.sub

    @staticmethod
    def extract_username(claims: TokenClaims) -> str:
        """Extract username from claims."""
        if not claims.preferred_username:
            raise MissingClaimError("preferred_username")
        return claims.preferred_username

    @staticmethod
    def extract_email(claims: TokenClaims) -> Optional[str]:
        """Extract email from claims."""
        return claims.email

    @staticmethod
    def extract_roles(claims: TokenClaims) -> list:
        """Extract roles from claims."""
        return claims.roles if claims.roles else []

    @staticmethod
    def extract_attributes(claims: TokenClaims) -> dict:
        """Extract custom attributes from claims."""
        return claims.attributes if claims.attributes else {}

    @staticmethod
    def extract_status(claims: TokenClaims) -> Optional[str]:
        """Extract user status from attributes."""
        return claims.attributes.get("status")

    @staticmethod
    def extract_ohr_id(claims: TokenClaims) -> Optional[str]:
        """Extract OHR ID from attributes."""
        return claims.attributes.get("ohr_id")

    @staticmethod
    def has_role(claims: TokenClaims, role_name: str) -> bool:
        """Check if user has a specific role."""
        return role_name in claims.roles

    @staticmethod
    def has_any_role(claims: TokenClaims, role_names: list) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in claims.roles for role in role_names)

    @staticmethod
    def is_company_email(email: Optional[str], company_domain: str) -> bool:
        """Check if email is from company domain."""
        if not email or "@" not in email:
            return False
        domain = email.split("@")[1]
        return domain == company_domain


# ==================== TOKEN EXCHANGER ====================

class TokenExchanger:
    """
    Handles Authorization Code exchange for tokens.
    
    Provides server-to-server token request to Keycloak using client credentials.
    """

    def __init__(self, config: Optional[KeycloakConfig] = None):
        """
        Initialize token exchanger.
        
        Args:
            config: Keycloak configuration
        """
        if config:
            self.config = config
        else:
            from keycloak_auth.config import get_keycloak_config
            self.config = get_keycloak_config()

    def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.
        
        Args:
            code: Authorization code from Keycloak redirect
            redirect_uri: Original redirect URI used in auth request
            
        Returns:
            Dictionary containing tokens (access_token, id_token, refresh_token)
            
        Raises:
            KeycloakAuthException: If token exchange fails
        """
        try:
            logger.info(f"Exchanging code for token at {self.config.token_endpoint}")
            
            data = {
                "grant_type": "authorization_code",
                "client_id": self.config.oidc_client_id,
                "code": code,
                "redirect_uri": redirect_uri,
            }
            
            # Add client secret if configured (Confidential client)
            if self.config.oidc_client_secret:
                data["client_secret"] = self.config.oidc_client_secret
                
            response = requests.post(
                self.config.token_endpoint,
                data=data,
                timeout=10
            )
            
            if not response.ok:
                error_data = {}
                try:
                    error_data = response.json()
                except:
                    pass
                
                error_msg = error_data.get("error_description") or error_data.get("error") or response.text
                logger.error(f"Token exchange failed ({response.status_code}): {error_msg}")
                raise KeycloakAuthException(f"Token exchange failed: {error_msg}")
                
            token_data = response.json()
            logger.info("Token exchange successful")
            return token_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during token exchange: {str(e)}")
            raise KeycloakAuthException(f"Could not connect to Keycloak for token exchange: {str(e)}")

    def exchange_keycloak_token_for_idp_token(self, access_token: str, provider: str = "okta") -> Dict[str, Any]:
        """
        Exchange a Keycloak Access Token for an external IDP token (e.g., Okta).
        
        Requires Token Exchange feature to be enabled in Keycloak and
        the client to have 'token-exchange' permission for the IDP.
        """
        try:
            logger.info(f"Exchanging Keycloak token for {provider} token")
            
            data = {
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "client_id": self.config.oidc_client_id,
                "subject_token": access_token,
                "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "requested_issuer": provider,
                "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
            }
            
            if self.config.oidc_client_secret:
                data["client_secret"] = self.config.oidc_client_secret
                
            response = requests.post(
                self.config.token_endpoint,
                data=data,
                timeout=10
            )
            
            if not response.ok:
                error_msg = response.text
                try:
                    error_msg = response.json().get("error_description") or response.text
                except:
                    pass
                logger.error(f"Token exchange for {provider} failed: {error_msg}")
                raise KeycloakAuthException(f"IDP Token exchange failed: {error_msg}")
                
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during IDP token exchange: {str(e)}")
            raise KeycloakAuthException(f"Could not connect to Keycloak for IDP token exchange: {str(e)}")
