from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from keycloak_auth import AuthenticatedUser, get_current_user, TokenExchanger
from app.schemas import SuccessResponse, TokenExchangeRequest
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/exchange", response_model=SuccessResponse)
async def exchange_token(
    req: TokenExchangeRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Exchange authorization code for access token and sync user to local DB.
    """
    try:
        exchanger = TokenExchanger()
        tokens = exchanger.exchange_code_for_token(
            code=req.code,
            redirect_uri=req.redirect_uri
        )
        
        # Sync user to DB after successful login
        from keycloak_auth.core import TokenValidator
        from keycloak_auth.config import get_keycloak_config
        from app.database import User
        from sqlalchemy.future import select
        
        # We validate the access token to get user info for syncing
        validator = TokenValidator(get_keycloak_config())
        claims = validator.validate_token(tokens["access_token"])
        
        # Robust Sync: Check by keycloak_id OR email OR username 
        from sqlalchemy import or_
        stmt = select(User).where(
            or_(
                User.keycloak_id == claims.sub,
                User.email == claims.email,
                User.username == claims.preferred_username
            )
        )
        result = await db.execute(stmt)
        db_user = result.scalars().first()
        
        # If user has 'Admin' or 'Portal Admin' role in Keycloak, they should be ACTIVE automatically
        is_admin = any(r.lower() in ["admin", "portal admin"] for r in claims.roles)
        initial_status = "ACTIVE" if is_admin else "PENDING"
        
        if not db_user:
            logger.info(f"Creating new user in local DB: {claims.preferred_username}")
            db_user = User(
                keycloak_id=claims.sub,
                email=claims.email,
                username=claims.preferred_username,
                first_name=claims.given_name,
                last_name=claims.family_name,
                status=initial_status,
                assigned_role="Admin" if is_admin else None,
                is_enabled=True
            )
            db.add(db_user)
        else:
            logger.info(f"Updating existing user in local DB: {db_user.username}")
            # Update info and re-link keycloak_id if it changed
            db_user.keycloak_id = claims.sub
            db_user.email = claims.email
            db_user.username = claims.preferred_username
            db_user.first_name = claims.given_name
            db_user.last_name = claims.family_name
            if is_admin:
                db_user.status = "ACTIVE"
                db_user.assigned_role = "Admin"
                
        await db.commit()
        
        return SuccessResponse(
            message="Token exchange and sync successful",
            data=tokens
        )
    except Exception as e:
        logger.error(f"Exchange/Sync failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Failed to exchange token: {str(e)}"
        )


@router.get("/me")
async def get_me(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Return the current logged in user details including roles."""
    roles = current_user.roles.copy() if current_user.roles else []
    
    # Okta-brokered logins don't always contain Realm Roles in the token.
    # Fallback to the local database to get the assigned_role!
    from app.database import User
    from sqlalchemy import or_, select
    
    stmt = select(User).where(
        or_(
            User.keycloak_id == current_user.user_id,
            User.email == current_user.email
        )
    )
    result = await db.execute(stmt)
    db_user = result.scalars().first()
    
    if db_user and db_user.assigned_role and db_user.assigned_role not in roles:
        roles.append(db_user.assigned_role)
        
    return {
        "user": {
            "id": current_user.user_id,
            "email": current_user.email,
            "roles": roles,
            "ohrid": db_user.ohr_id if db_user else None,
            "status": db_user.status if db_user else "UNKNOWN"
        }
    }
