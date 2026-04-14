import sys
import os
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

# Add parent directories and all internal packages to path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, '..', 'keycloak_auth'))
sys.path.append(os.path.join(BASE_DIR, '..', 'rbac_system'))
sys.path.append(os.path.join(BASE_DIR, '..', 'taskflow_system'))

# Mock database and Keycloak dependencies
mock_tokens = {"access_token": "mock_token"}

async def verify_login_logic():
    print("--- Starting Verification of Corporate Auth Logic ---")
    
    # We need to import the function we want to test
    from app.api.auth import exchange_token
    from app.schemas import TokenExchangeRequest
    from keycloak_auth.models import TokenClaims
    from fastapi import HTTPException

    request = TokenExchangeRequest(code="test_code", redirect_uri="http://localhost")
    mock_db = MagicMock()

    # Scenario 1: Personal Email (Gmail) - Should be Restricted
    print("\nScenario 1: Testing Restricted Domain (user@gmail.com)...")
    claims_gmail = TokenClaims(
        sub="user123",
        email="user@gmail.com",
        preferred_username="user_gmail",
        roles=[],
        exp=9999999999,
        iat=0,
        raw_payload={}
    )
    
    with patch("keycloak_auth.TokenExchanger.exchange_code_for_token", return_value=mock_tokens):
        with patch("keycloak_auth.core.TokenValidator.validate_token", return_value=claims_gmail):
            try:
                await exchange_token(request, mock_db)
                print("FAILED: Login with @gmail.com was NOT blocked.")
            except HTTPException as e:
                if e.status_code == 403:
                    print(f"PASSED: Blocked with 403 Forbidden. Message: {e.detail}")
                else:
                    print(f"FAILED: Got unexpected error code {e.status_code}")

    # Scenario 2: Corporate Email (@cenrixa.local) - Should be Auto-Approved
    print("\nScenario 2: Testing Auto-Approval Domain (emp456@cenrixa.local)...")
    claims_corp = TokenClaims(
        sub="emp456",
        email="emp456@cenrixa.local",
        preferred_username="emp456",
        roles=[], # No roles in Keycloak
        exp=9999999999,
        iat=0,
        raw_payload={}
    )
    
    # Mock database responses for sync
    mock_db.execute = AsyncMock()
    mock_db_res = MagicMock()
    mock_db.execute.return_value = mock_db_res
    mock_db_res.scalars.return_value.first.return_value = None # Simulate New User creation
    mock_db.commit = AsyncMock()
    
    with patch("keycloak_auth.TokenExchanger.exchange_code_for_token", return_value=mock_tokens):
        with patch("keycloak_auth.core.TokenValidator.validate_token", return_value=claims_corp):
            # Capture what's added to the DB
            added_entities = []
            mock_db.add = lambda x: added_entities.append(x)
            
            with patch.object(mock_db, "commit", return_value=None):
                await exchange_token(request, mock_db)
                
                if added_entities:
                    new_user = added_entities[0]
                    print(f"PASSED: User created in DB.")
                    print(f"   Status: {new_user.status}")
                    print(f"   Role: {new_user.assigned_role}")
                    
                    if new_user.status == "ACTIVE" and new_user.assigned_role == "Trainee":
                        print("VERIFIED: @cenrixa.local users are ACTIVE Trainees automatically.")
                    else:
                        print("FAILED: Status or Role is incorrect for auto-approval.")
                else:
                    print("FAILED: No user was added to DB session.")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    asyncio.run(verify_login_logic())
