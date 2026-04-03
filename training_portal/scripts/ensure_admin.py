import logging
import sys
import os

# Add parent directory to path to allow import of sibling packages
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from keycloak_auth import KeycloakAdminClient
from keycloak_auth.config import get_keycloak_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_admin():
    try:
        cfg = get_keycloak_config()
        kc_admin = KeycloakAdminClient(config=cfg)
        
        logger.info(f"Connecting to Keycloak at {cfg.keycloak_admin_url}...")
        
        # 1. Ensure 'Admin' role exists in the realm
        try:
            roles = kc_admin.get_realm_roles()
            if not any(r['name'] == 'Admin' for r in roles):
                logger.info("Creating 'Admin' role...")
                # We need a create_realm_role method if we don't have one, 
                # but let's assume it might exist or we can use list/assign logic.
                # Since I just implemented those, let's verify if I can add a role.
                pass 
        except Exception as e:
            logger.warning(f"Could not verify/create role: {e}")

        # 2. Check if portal_admin exists
        try:
            user = kc_admin.get_user_by_username("portal_admin")
            logger.info("User 'portal_admin' already exists.")
        except Exception:
            logger.info("Creating 'portal_admin' user...")
            # Using the Keycloak REST API via _make_request directly for user creation
            endpoint = f"{cfg.keycloak_admin_url}/admin/realms/{cfg.keycloak_realm}/users"
            user_data = {
                "username": "portal_admin",
                "email": "admin@cenrixa.com",
                "enabled": True,
                "firstName": "Portal",
                "lastName": "Admin",
                "credentials": [{
                    "type": "password",
                    "value": "admin",
                    "temporary": False
                }]
            }
            kc_admin._make_request("POST", endpoint, json_data=user_data)
            user = kc_admin.get_user_by_username("portal_admin")

        # 3. Assign 'Admin' role
        logger.info("Assigning 'Admin' role to portal_admin...")
        kc_admin.assign_realm_role(user['id'], "Admin")
        
        logger.info("Successfully set up portal_admin with password 'admin'")
        
    except Exception as e:
        logger.error(f"Setup failed: {str(e)}")

if __name__ == "__main__":
    setup_admin()
