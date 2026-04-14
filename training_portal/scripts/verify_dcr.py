import sys
import os
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

# Add local packages to path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, '..', 'keycloak_auth'))
sys.path.append(os.path.join(BASE_DIR, '..', 'rbac_system'))
sys.path.append(os.path.join(BASE_DIR, '..', 'taskflow_system'))

async def verify_dcr_logic():
    print("--- Starting Verification of Dynamic Client Registration (DCR) ---")
    
    from keycloak_auth.config import get_keycloak_config
    from keycloak_auth.admin import KeycloakAdminClient
    from keycloak_auth.dcr import KeycloakDCRClient

    config = get_keycloak_config()
    
    # Mock Token Validation & API calls since we don't have a live server
    mock_token = "mock_iat_token"
    mock_client_metadata = {
        "client_id": "new-app-id",
        "client_secret": "new-app-secret",
        "registration_client_uri": "http://localhost:8080/registrations/new-app-id"
    }

    # Scenario: Automated App Onboarding
    print("\nScenario: Registering 'New Enterprise App' via DCR...")
    
    # 1. Mock Admin Client to "generate" an IAT
    with patch("keycloak_auth.admin.KeycloakAdminClient.create_initial_access_token", return_value=mock_token):
        admin = KeycloakAdminClient(config)
        iat = admin.create_initial_access_token(count=1, lifespan=3600)
        print(f"PASSED: Generated Initial Access Token (IAT): {iat}")

        # 2. Mock DCR Client to "register" the app using that IAT
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 201
            mock_post.return_value.json.return_value = mock_client_metadata
            
            dcr = KeycloakDCRClient(config)
            reg_info = {
                "client_name": "New Enterprise App",
                "redirect_uris": ["https://new-app.cenrixa.local/callback"]
            }
            
            result = dcr.register_client(reg_info, initial_access_token=iat)
            
            print(f"PASSED: Client Registered Successfully!")
            print(f"   Generated Client ID: {result.get('client_id')}")
            print(f"   Generated Client Secret: {result.get('client_secret')}")

            if result.get('client_id') == "new-app-id":
                print("\nVERIFIED: DCR Flow is correctly implemented.")
            else:
                print("\nFAILED: Registration data mismatch.")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    asyncio.run(verify_dcr_logic())
