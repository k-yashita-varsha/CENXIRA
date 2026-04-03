import os
import httpx
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class OktaService:
    """Service to interact with Okta Management API."""
    
    def _get_credentials(self):
        """Lazily read credentials from env at call time (not import time)."""
        api_token = os.getenv("OKTA_API_TOKEN")
        issuer_url = os.getenv("OKTA_ISSUER_URL", "")
        base_url = issuer_url.split('/oauth2')[0].rstrip('/')
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"SSWS {api_token}"
        }
        return api_token, base_url, headers

    async def create_corporate_user(
        self, 
        ohrid: str, 
        email: str, 
        password: str, 
        first_name: str, 
        last_name: str
    ) -> bool:
        """
        Create a user in Okta with the provided OHRID as login.
        """
        # Read env vars lazily so they are always fresh from the loaded .env
        api_token, base_url, headers = self._get_credentials()
        
        if not api_token:
            logger.error("OKTA_API_TOKEN not found in environment! Okta sync skipped.")
            return False

        endpoint = f"{base_url}/api/v1/users?activate=true"
        
        # In Okta IDX, 'login' must be in email format. 
        # We use your OHRID with a internal domain to keep it unique and corporate.
        okta_login = f"{ohrid}@cenrixa.local"
        
        user_data = {
            "profile": {
                "firstName": first_name or "First",
                "lastName": last_name or "Last",
                "email": email,
                "login": okta_login
            },
            "credentials": {
                "password" : { "value": password }
            }
        }

        logger.info(f"Creating Okta user {okta_login} at {endpoint}...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(endpoint, headers=headers, json=user_data)
                
                if response.status_code == 200:
                    logger.info(f"User {ohrid} successfully synced to Okta.")
                    return True
                elif response.status_code == 409:
                    # User already exists - still a success for our purposes
                    logger.warning(f"User {ohrid} already exists in Okta (409).")
                    return True
                else:
                    try:
                        error_data = response.json()
                        logger.error(f"Okta sync failed for {ohrid}: {response.status_code} - {error_data}")
                    except Exception:
                        logger.error(f"Okta sync failed for {ohrid}: {response.status_code} - {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Error syncing user to Okta: {str(e)}")
            return False

okta_service = OktaService()
