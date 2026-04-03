"""
Keycloak Admin API client.

Manages user operations via Keycloak Admin REST API.
Handles user CRUD, attribute management, and user lifecycle operations.
"""

import logging
import time
from typing import Dict, Any, Optional, List

import requests

from keycloak_auth.config import KeycloakConfig
from keycloak_auth.core import (
    AdminAPIError,
    KeycloakConnectionError,
    UserNotFoundError,
)

logger = logging.getLogger(__name__)


class KeycloakAdminClient:
    """
    Keycloak Admin API client.
    
    Provides methods to manage users via Keycloak Admin REST API.
    Handles authentication, caching of admin token, and error handling.
    """

    def __init__(self, config: KeycloakConfig):
        """
        Initialize Keycloak Admin client.
        
        Args:
            config: Keycloak configuration
        """
        self.config = config
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[float] = None
        logger.info("KeycloakAdminClient initialized")

    def _get_admin_token(self) -> str:
        """
        Get admin access token from Keycloak.
        
        Uses cached token if still valid, otherwise requests new token.
        
        Returns:
            Admin access token
            
        Raises:
            AdminAPIError: If token retrieval fails
            KeycloakConnectionError: If connection fails
        """
        # Use cached token if valid
        if self.access_token and self.token_expires_at:
            if time.time() < self.token_expires_at - 30:  # 30 sec buffer
                logger.debug("Using cached admin token")
                return self.access_token

        try:
            logger.debug("Requesting admin token from Keycloak")
            response = requests.post(
                self.config.admin_token_endpoint,
                data={
                    "grant_type": "password",
                    "client_id": self.config.keycloak_admin_client_id,
                    "username": self.config.keycloak_admin_username,
                    "password": self.config.keycloak_admin_password,
                },
                timeout=10,
            )
            response.raise_for_status()

            data = response.json()
            self.access_token = data["access_token"]

            expires_in = data.get("expires_in", 3600)
            self.token_expires_at = time.time() + expires_in

            logger.info("Admin token obtained successfully")
            return self.access_token

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error getting admin token: {str(e)}")
            raise KeycloakConnectionError(f"Failed to connect to Keycloak: {str(e)}")
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout getting admin token: {str(e)}")
            raise KeycloakConnectionError(f"Keycloak connection timeout: {str(e)}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting admin token: {str(e)}")
            raise AdminAPIError(f"Failed to get admin token: {str(e)}")
        except KeyError as e:
            logger.error(f"Invalid token response: {str(e)}")
            raise AdminAPIError(f"Invalid token response: {str(e)}")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Make authenticated request to Admin API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint URL
            json_data: JSON request body
            params: Query parameters
            
        Returns:
            Response JSON (or None for 204 No Content)
            
        Raises:
            AdminAPIError: If request fails
            UserNotFoundError: If resource not found (404)
        """
        token = self._get_admin_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.request(
                method=method,
                url=endpoint,
                json=json_data,
                params=params,
                headers=headers,
                timeout=10,
            )

            # Handle 204 No Content
            if response.status_code == 204:
                return None

            response.raise_for_status()

            if response.content:
                return response.json()
            return None

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error from Admin API: {str(e)}")
            status_code = e.response.status_code

            if status_code == 404:
                raise UserNotFoundError(f"Resource not found: {endpoint}")
            else:
                raise AdminAPIError(f"Admin API error: {str(e)}", status_code=status_code)
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error to Admin API: {str(e)}")
            raise AdminAPIError(f"Admin API request failed: {str(e)}")

    def get_user(self, user_id: str) -> Dict[str, Any]:
        """
        Get user by ID.
        
        Args:
            user_id: Keycloak user ID
            
        Returns:
            User information dictionary
        """
        logger.debug(f"Getting user: {user_id}")
        endpoint = f"{self.config.admin_users_url}/{user_id}"
        return self._make_request("GET", endpoint)

    def get_user_by_username(self, username: str) -> Dict[str, Any]:
        """
        Get user by username.
        
        Args:
            username: Keycloak username
            
        Returns:
            User information (returns first match if multiple)
        """
        logger.debug(f"Getting user by username: {username}")
        response = self._make_request(
            "GET", self.config.admin_users_url, params={"username": username}
        )

        if not response or len(response) == 0:
            raise UserNotFoundError(f"User not found: {username}")

        return response[0]

    def get_user_by_email(self, email: str) -> Dict[str, Any]:
        """
        Get user by email.
        
        Args:
            email: User email
            
        Returns:
            User information
        """
        logger.debug(f"Getting user by email: {email}")
        response = self._make_request(
            "GET", self.config.admin_users_url, params={"email": email}
        )

        if not response or len(response) == 0:
            raise UserNotFoundError(f"User not found with email: {email}")

        return response[0]

    def update_user(self, user_id: str, user_data: Dict[str, Any]) -> None:
        """
        Update user information.
        
        Args:
            user_id: Keycloak user ID
            user_data: User data to update (e.g., {'email': 'new@email.com', 'firstName': 'John'})
        """
        logger.info(f"Updating user: {user_id}")
        endpoint = f"{self.config.admin_users_url}/{user_id}"
        self._make_request("PUT", endpoint, json_data=user_data)
        logger.info(f"User updated: {user_id}")

    def set_user_attributes(self, user_id: str, attributes: Dict[str, Any]) -> None:
        """
        Set custom attributes on user.
        
        Attributes are merged with existing attributes.
        
        Args:
            user_id: Keycloak user ID
            attributes: Dictionary of attributes to set (e.g., {'status': 'ACTIVE', 'ohr_id': 'john@company.com'})
        """
        logger.info(f"Setting attributes on user: {user_id}")

        # Get current user
        user = self.get_user(user_id)

        # Merge attributes
        current_attrs = user.get("attributes", {})
        updated_attrs = {**current_attrs, **attributes}

        # Update user with new attributes
        self.update_user(user_id, {"attributes": updated_attrs})
        logger.info(f"Attributes set on user {user_id}: {list(attributes.keys())}")

    def get_user_attributes(self, user_id: str) -> Dict[str, Any]:
        """
        Get all custom attributes for user.
        
        Args:
            user_id: Keycloak user ID
            
        Returns:
            Dictionary of user attributes
        """
        logger.debug(f"Getting attributes for user: {user_id}")
        user = self.get_user(user_id)
        return user.get("attributes", {})

    def get_user_attribute(self, user_id: str, attribute_name: str) -> Any:
        """
        Get specific custom attribute for user.
        
        Args:
            user_id: Keycloak user ID
            attribute_name: Attribute name to retrieve
            
        Returns:
            Attribute value or None
        """
        logger.debug(f"Getting attribute '{attribute_name}' for user: {user_id}")
        attributes = self.get_user_attributes(user_id)
        return attributes.get(attribute_name)

    def update_user_email(self, user_id: str, new_email: str) -> None:
        """
        Update user email.
        
        Args:
            user_id: Keycloak user ID
            new_email: New email address
        """
        logger.info(f"Updating email for user {user_id} to {new_email}")
        self.update_user(user_id, {"email": new_email, "emailVerified": False})

    def set_user_enabled(self, user_id: str, enabled: bool) -> None:
        """
        Enable or disable user account.
        
        Args:
            user_id: Keycloak user ID
            enabled: True to enable, False to disable
        """
        status = "enabled" if enabled else "disabled"
        logger.info(f"Setting user {user_id} {status}")
        self.update_user(user_id, {"enabled": enabled})

    def set_user_password(
        self, user_id: str, password: str, temporary: bool = False
    ) -> None:
        """
        Set user password.
        
        Args:
            user_id: Keycloak user ID
            password: New password
            temporary: If True, user must change password on first login
        """
        logger.info(f"Setting password for user {user_id}")
        endpoint = f"{self.config.admin_users_url}/{user_id}/reset-password"
        self._make_request(
            "PUT",
            endpoint,
            json_data={
                "type": "password",
                "value": password,
                "temporary": temporary,
            },
        )

    def send_verify_email(self, user_id: str, redirect_uri: Optional[str] = None) -> None:
        """
        Send email verification email to user.
        
        Args:
            user_id: Keycloak user ID
            redirect_uri: Optional redirect URI after email verification
        """
        logger.info(f"Sending verification email to user {user_id}")
        endpoint = f"{self.config.admin_users_url}/{user_id}/send-verify-email"
        params = {}
        if redirect_uri:
            params["redirect_uri"] = redirect_uri
        self._make_request("PUT", endpoint, params=params)

    def list_users(
        self, search: Optional[str] = None, max_results: int = 100, first: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List users with optional search.
        
        Args:
            search: Optional search string (searches username, email, name)
            max_results: Maximum number of results
            first: Offset for pagination
            
        Returns:
            List of user objects
        """
        logger.debug(f"Listing users (search: {search}, max: {max_results})")
        params = {
            "max": max_results,
            "first": first,
        }
        if search:
            params["search"] = search

        return self._make_request("GET", self.config.admin_users_url, params=params) or []

    def get_users(self) -> List[Dict[str, Any]]:
        """Alias for list_users with default settings."""
        return self.list_users()

    def get_user_realm_roles(self, user_id: str) -> List[Dict[str, Any]]:
        """Get realm-level roles assigned to user."""
        logger.debug(f"Getting realm roles for user: {user_id}")
        endpoint = f"{self.config.admin_users_url}/{user_id}/role-mappings/realm"
        return self._make_request("GET", endpoint) or []

    def get_realm_roles(self) -> List[Dict[str, Any]]:
        """List all roles in the realm."""
        logger.debug("Listing all realm roles")
        endpoint = f"{self.config.admin_url}/roles"
        return self._make_request("GET", endpoint) or []

    def assign_realm_role(self, user_id: str, role_name: str) -> None:
        """Assign realm-level role to user by name."""
        logger.info(f"Assigning role '{role_name}' to user {user_id}")
        
        # 1. Find role object to get its ID
        roles = self.get_realm_roles()
        target_role = next((r for r in roles if r["name"] == role_name), None)
        
        if not target_role:
            logger.error(f"Role '{role_name}' not found in realm")
            raise AdminAPIError(f"Role '{role_name}' not found")
            
        # 2. Assign the role
        endpoint = f"{self.config.admin_users_url}/{user_id}/role-mappings/realm"
        self._make_request("POST", endpoint, json_data=[target_role])
        logger.info(f"Role '{role_name}' assigned to user {user_id}")

    def delete_user(self, user_id: str) -> None:
        """Delete user from Keycloak."""
        logger.info(f"Deleting user: {user_id}")
        endpoint = f"{self.config.admin_users_url}/{user_id}"
        self._make_request("DELETE", endpoint)
        logger.info(f"User deleted: {user_id}")

    def add_identity_provider(self, idp_config: dict) -> None:
        """
        Configure an external Identity Provider (e.g., Google, Okta) in the realm.
        """
        idp_alias = idp_config.get("alias")
        endpoint = f"{self.config.admin_url}/identity-provider/instances"
        try:
            self._make_request("GET", f"{endpoint}/{idp_alias}")
            return
        except Exception:
            pass
        self._make_request("POST", endpoint, json_data=idp_config)

    def set_user_required_actions(self, user_id: str, actions: list) -> None:
        """
        Set required actions for a user (e.g., ['UPDATE_PASSWORD', 'CONFIGURE_TOTP']).
        """
        endpoint = f"{self.config.admin_users_url}/{user_id}"
        self._make_request("PUT", endpoint, json_data={"requiredActions": actions})


    def remove_identity_provider(self, idp_alias: str) -> None:
        """
        Delete an Identity Provider configuration from the realm.
        """
        logger.info(f"Removing identity provider: {idp_alias}")
        endpoint = f"{self.config.admin_url}/identity-provider/instances/{idp_alias}"
        try:
            self._make_request("DELETE", endpoint)
            logger.info(f"Identity provider '{idp_alias}' removed successfully.")
        except Exception as e:
            logger.warning(f"Failed to remove identity provider '{idp_alias}': {str(e)}")


    def list_identity_providers(self) -> list:
        """
        List all identity providers configured in the realm.
        """
        endpoint = f"{self.config.admin_url}/identity-provider/instances"
        return self._make_request("GET", endpoint) or []


    def update_identity_provider(self, idp_alias: str, idp_config: dict) -> None:
        """
        Forcefully update an existing Identity Provider configuration.
        """
        logger.info(f"Force-updating identity provider: {idp_alias}")
        endpoint = f"{self.config.admin_url}/identity-provider/instances/{idp_alias}"
        self._make_request("PUT", endpoint, json_data=idp_config)
