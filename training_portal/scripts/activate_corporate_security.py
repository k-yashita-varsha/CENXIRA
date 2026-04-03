import sys
import os
import logging
from dotenv import load_dotenv

# Add parent directories to path to import local modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'keycloak_auth')))

from keycloak_auth.config import KeycloakConfig
from keycloak_auth.admin import KeycloakAdminClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    load_dotenv()
    
    # 1. Initialize Keycloak Admin Client
    config = KeycloakConfig(
        keycloak_admin_url=os.getenv("KEYCLOAK_ADMIN_URL"),
        keycloak_realm=os.getenv("KEYCLOAK_REALM"),
        keycloak_admin_client_id=os.getenv("KEYCLOAK_ADMIN_CLIENT_ID", "admin-cli"),
        keycloak_admin_username=os.getenv("KEYCLOAK_ADMIN_USERNAME"),
        keycloak_admin_password=os.getenv("KEYCLOAK_ADMIN_PASSWORD")
    )
    kc_admin = KeycloakAdminClient(config)
    
    # 2. Configure Google Identity Provider
    google_client_id = os.getenv("GOOGLE_CLIENT_ID")
    google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    if google_client_id and google_client_secret:
        logger.info("Enabling Google Identity Provider...")
        google_config = {
            "alias": "google",
            "providerId": "google",
            "enabled": True,
            "config": {
                "clientId": google_client_id,
                "clientSecret": google_client_secret,
                "useJwksUrl": "true"
            }
        }
        kc_admin.add_identity_provider(google_config)
    else:
        logger.warning("Google credentials not found in .env, skipping.")

    # 3. Configure Okta Identity Provider (OIDC)
    okta_client_id = os.getenv("OKTA_CLIENT_ID")
    okta_client_secret = os.getenv("OKTA_CLIENT_SECRET")
    okta_issuer = os.getenv("OKTA_ISSUER_URL")
    
    if okta_client_id and okta_client_secret and okta_issuer:
        logger.info("Enabling Okta (OIDC) Identity Provider...")
        
        # Determine if it's a Custom AS or Org AS
        base_endpoint = okta_issuer if "/oauth2/" in okta_issuer else f"{okta_issuer}/oauth2"
        
        okta_config = {
            "alias": "okta",
            "displayName": "Okta Corporate",
            "providerId": "oidc",
            "enabled": True,
            "config": {
                "clientId": okta_client_id,
                "clientSecret": okta_client_secret,
                "authorizationUrl": f"{base_endpoint}/v1/authorize",
                "tokenUrl": f"{base_endpoint}/v1/token",
                "userInfoUrl": f"{base_endpoint}/v1/userinfo",
                "jwksUrl": f"{base_endpoint}/v1/keys",
                "issuer": okta_issuer,
                "useJwksUrl": "true"
            }
        }
        
        # 1. Discover and Purge ALL old Okta instances
        try:
            idps = kc_admin.list_identity_providers()
            for idp in idps:
                alias = idp.get("alias", "").lower()
                display = idp.get("displayName", "").lower()
                if "okta" in alias or "okta" in display:
                    logger.info(f"Purging old Okta instance: {idp.get('alias')}")
                    kc_admin.remove_identity_provider(idp.get("alias"))
        except Exception as e:
            logger.warning(f"Failed to scan/purge identity providers: {str(e)}")
            
        # 2. Add the fresh instance
        kc_admin.add_identity_provider(okta_config)
    else:
        logger.warning("Okta credentials not found in .env, skipping.")

    logger.info("Corporate Security Activation Complete!")
    logger.info("The Keycloak Login Screen should now display Google and Okta options.")

if __name__ == "__main__":
    main()
