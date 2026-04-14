import logging
import requests
from typing import Dict, Any, Optional
from keycloak_auth.config import KeycloakConfig

logger = logging.getLogger(__name__)

class KeycloakDCRClient:
    """
    OIDC Dynamic Client Registration (DCR) client.
    
    Allows automated registration of new OIDC clients in Keycloak.
    """

    def __init__(self, config: KeycloakConfig):
        self.config = config
        logger.info("KeycloakDCRClient initialized")

    def register_client(self, metadata: Dict[str, Any], initial_access_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Register a new OIDC client via standard DCR endpoint.
        
        Args:
            metadata: Client metadata (client_name, redirect_uris, etc.)
            initial_access_token: Optional IAT for authorized registration
            
        Returns:
            Keycloak response including client_id and registration_access_token
        """
        logger.info(f"Registering new client: {metadata.get('client_name')}")
        
        headers = {"Content-Type": "application/json"}
        if initial_access_token:
            headers["Authorization"] = f"Bearer {initial_access_token}"
            
        try:
            response = requests.post(
                self.config.dcr_registration_url,
                json=metadata,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Client registered successfully: {data.get('client_id')}")
            return data
        except requests.exceptions.HTTPError as e:
            logger.error(f"DCR Registration failed: {str(e)} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"DCR Registration failed: {str(e)}")
            raise

    def get_client(self, registration_uri: str, registration_access_token: str) -> Dict[str, Any]:
        """
        Retrieve client metadata using the registration access token.
        """
        headers = {"Authorization": f"Bearer {registration_access_token}"}
        response = requests.get(registration_uri, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()

    def delete_client(self, registration_uri: str, registration_access_token: str) -> None:
        """
        Delete a client using the registration access token.
        """
        headers = {"Authorization": f"Bearer {registration_access_token}"}
        response = requests.delete(registration_uri, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info(f"Client at {registration_uri} deleted successfully")
