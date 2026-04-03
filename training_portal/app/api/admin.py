from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Dict, Any
import string
import random
from uuid import UUID

from sqlalchemy import func, desc
from app.database import get_db, User, Role, AuditLog
from app.schemas import UserResponse, SuccessResponse
from pydantic import BaseModel
import logging

from keycloak_auth import get_current_user, AuthenticatedUser
from keycloak_auth.config import get_keycloak_config
from rbac_system import require_role

# Import our new services
from app.services.email import EmailService
from app.services.okta import OktaService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])
email_service = EmailService()
okta_service = OktaService()

class UserApproveRequest(BaseModel):
    role_name: str

def generate_temp_password(length=12):
    """Generate a random temporary password (Alphanumeric for IdP compatibility)."""
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))

def generate_ohrid():
    """Generate a random company ID like EMP48271."""
    return f"EMP{random.randint(10000, 99999)}"

def _get_kc_admin():
    """Helper to get authorized Keycloak Admin Client."""
    from keycloak_auth import KeycloakAdminClient
    cfg = get_keycloak_config()
    return KeycloakAdminClient(config=cfg)

@router.get("/debug/me")
async def debug_me(
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Debug endpoint to see your own roles and claims."""
    return {
        "user_id": user.user_id,
        "username": user.username,
        "roles": user.roles,
        "attributes": user.attributes,
        "is_admin_check": "admin" in [r.lower() for r in user.roles]
    }

@router.get("/dashboard", response_model=SuccessResponse)
async def get_admin_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role(["Admin", "Portal Admin"]))
):
    """Get overview stats for the admin dashboard."""
    try:
        # Total users
        total_stmt = select(func.count(User.id))
        total_res = await db.execute(total_stmt)
        total_users = total_res.scalar() or 0

        # Pending users (from Keycloak)
        active_stmt = select(User.email).where(User.status == "ACTIVE")
        active_res = await db.execute(active_stmt)
        active_emails = {email for email in active_res.scalars().all() if email}

        kc_admin = _get_kc_admin()
        all_kc_users = kc_admin.get_users()
        pending_count = 0
        for user in all_kc_users:
            email = user.get("email")
            if email and email in active_emails:
                continue

            kc_id = user.get("id")
            roles = kc_admin.get_user_realm_roles(kc_id)
            role_names = [r.get("name") for r in roles]
            if not any(r in role_names for r in ["Admin", "Manager", "Trainee", "Portal Admin"]):
                pending_count += 1

        # Recent audit logs count
        audit_stmt = select(func.count(AuditLog.id))
        audit_res = await db.execute(audit_stmt)
        total_logs = audit_res.scalar() or 0

        return SuccessResponse(data={
            "total_users": total_users,
            "pending_approvals": pending_count,
            "total_roles": 3, # Fixed seeded roles
            "system_health": "Healthy",
            "active_sessions": 1,
            "total_logs": total_logs
        })
    except Exception as e:
        logger.error(f"Dashboard stats failed: {str(e)}")
        # Return zeros instead of failing hard
        return SuccessResponse(data={
            "total_users": 0,
            "pending_approvals": 0,
            "system_health": "Degraded",
            "active_sessions": 0,
            "total_logs": 0
        })


@router.get("/pending-users", response_model=SuccessResponse)
async def get_pending_users(
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role(["Admin", "Portal Admin"]))
):
    """
    Get all pending registrations directly from Keycloak.
    A 'pending' user is defined as someone who has registered in Keycloak
    but has not been assigned a system role (Admin, Manager, Trainee) yet.
    We also cross-reference with our database to filter out already-active users.
    """
    try:
        # Get emails of users who are already active in our DB
        active_stmt = select(User.email).where(User.status == "ACTIVE")
        active_res = await db.execute(active_stmt)
        active_emails = {email for email in active_res.scalars().all() if email}

        kc_admin = _get_kc_admin()
        all_kc_users = kc_admin.get_users()
        
        pending_users = []
        for user in all_kc_users:
            kc_id = user.get("id")
            email = user.get("email")
            
            # If the email is already ACTIVE in our system, do not count them as pending
            if email and email in active_emails:
                continue

            roles = kc_admin.get_user_realm_roles(kc_id)
            role_names = [r.get("name") for r in roles]
            
            # If they don't have our core roles, they are pending
            if not any(r in role_names for r in ["Admin", "Manager", "Trainee", "Portal Admin"]):
                pending_users.append({
                    "keycloak_id": kc_id,
                    "email": email,
                    "username": user.get("username"),
                    "first_name": user.get("firstName"),
                    "last_name": user.get("lastName"),
                    "status": "PENDING"
                })
                
        return SuccessResponse(data=pending_users)
        
    except Exception as e:
        logger.error(f"Failed to fetch pending users from Keycloak: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch users from Identity Provider.")


@router.post("/users/{keycloak_id}/approve", response_model=SuccessResponse)
async def approve_user(
    keycloak_id: str,
    req: UserApproveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role(["Admin", "Portal Admin"]))
):
    """Approve Keycloak user, assign role, dispatch email, and save to local DB."""
    if req.role_name not in ["Admin", "Manager", "Trainee", "Portal Admin"]:
        raise HTTPException(status_code=400, detail="Invalid role specified.")
        
    # Check if they are already in our local DB
    stmt = select(User).where(User.keycloak_id == keycloak_id)
    result = await db.execute(stmt)
    existing_db_user = result.scalars().first()
    
    if existing_db_user and existing_db_user.status == "ACTIVE":
        raise HTTPException(status_code=400, detail="User is already active.")
        
    try:
        kc_admin = _get_kc_admin()
        
        # 1. Fetch the user details from Keycloak
        kc_user = kc_admin.get_user(keycloak_id)
        if not kc_user:
            raise HTTPException(status_code=404, detail="User not found in Keycloak.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Keycloak operation failed: {str(e)}")

    ohrid = generate_ohrid()
    temp_password = "Temp123!" # generate_temp_password()
    email_to = kc_user.get("email")

    if not email_to:
        raise HTTPException(status_code=400, detail="Keycloak user has no email address configured.")

    try:
        # 2. Assign Role 
        kc_admin.assign_realm_role(user_id=keycloak_id, role_name=req.role_name)

        # 3. Set Temporary Password (forces reset on login)
        kc_admin.set_user_password(user_id=keycloak_id, password=temp_password, temporary=True)
        
        # 4. Mandatory Security: Force Password Reset for Local Login
        kc_admin.set_user_required_actions(keycloak_id, ["UPDATE_PASSWORD"])

        # 5. Update Keycloak Attributes (Optional: save OHRID to their profile)
        kc_admin.update_user(keycloak_id, {
            "attributes": {
                "ohrid": [ohrid]
            }
        })
        
        # 5. Insert into local Postgres DB
        if existing_db_user:
            db_user = existing_db_user
            db_user.status = "ACTIVE"
            db_user.is_enabled = True
            db_user.ohr_id = ohrid
            db_user.assigned_role = req.role_name
        else:
            db_user = User(
                keycloak_id=keycloak_id,
                email=email_to,
                username=kc_user.get("username"),
                first_name=kc_user.get("firstName"),
                last_name=kc_user.get("lastName"),
                ohr_id=ohrid,
                assigned_role=req.role_name,
                status="ACTIVE",
                is_enabled=True
            )
            db.add(db_user)
            
        await db.commit()
        await db.refresh(db_user)
        
        # 6. Real-Time Sync to Okta (Ultimate Corporate Experience)
        # This mirrors the account and credentials to Okta on-the-fly
        okta_status = await okta_service.create_corporate_user(
            ohrid=ohrid,
            email=email_to,
            password=temp_password,
            first_name=kc_user.get("firstName"),
            last_name=kc_user.get("lastName")
        )

        logger.info(f"User {ohrid} sync to Okta status: {okta_status}")

    except Exception as e:
        logger.error(f"Approval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to complete approval workflow: {str(e)}")
        
    # 6. Dispatch Email with Credentials
    try:
        email_service.send_approval_email(email_to, ohrid, temp_password)
    except Exception as e:
        # We don't want to rollback the whole approval just because email failed, 
        # but we should let the admin know.
        return SuccessResponse(
            message="User approved successfully, BUT email dispatch failed. Please share credentials manually.",
            data={
                "user_id": str(db_user.id),
                "ohrid": ohrid,
                "temp_password": temp_password,
                "role": req.role_name,
                "email_failed": True
            }
        )

    return SuccessResponse(
        message="User approved successfully and email sent.",
        data={
            "user_id": str(db_user.id),
            "ohrid": ohrid,
            "role": req.role_name
        }
    )

@router.post("/users/{keycloak_id}/reject", response_model=SuccessResponse)
async def reject_user(
    keycloak_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role(["Admin", "Portal Admin"]))
):
    """Reject a pending registration by removing them from Keycloak, or labeling them rejected."""
    try:
        kc_admin = _get_kc_admin()
        # Natively delete the user from Keycloak so they can't login
        kc_admin.delete_user(keycloak_id)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove user from identity provider: {str(e)}")
    
    # Check if they randomly existed in DB
    stmt = select(User).where(User.keycloak_id == keycloak_id)
    result = await db.execute(stmt)
    db_user = result.scalars().first()
    
    if db_user:
        db_user.status = "REJECTED"
        await db.commit()
    
    return SuccessResponse(message="User registration rejected and deleted from Keycloak.")


@router.delete("/users/{user_id}", response_model=SuccessResponse)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role(["Admin", "Portal Admin"]))
):
    """Permanently delete a user from local DB and Keycloak."""
    try:
        # 1. Find user in local DB
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        db_user = result.scalars().first()
        
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
            
        # 2. Delete from Keycloak
        try:
            kc_admin = _get_kc_admin()
            kc_admin.delete_user(db_user.keycloak_id)
        except Exception as ke:
            logger.warning(f"Could not delete user {db_user.email} from Keycloak (might already be gone): {ke}")
            
        # 3. Delete from Local DB
        await db.delete(db_user)
        await db.commit()
        
        return SuccessResponse(message=f"User {db_user.email} successfully deleted from all systems.")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal deletion error: {str(e)}")


@router.get("/users", response_model=SuccessResponse)
async def get_all_users(
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role(["Admin", "Portal Admin"]))
):
    """Get all active users from local DB."""
    stmt = select(User)
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    users_data = []
    for u in users:
        u_dict = UserResponse.model_validate(u).model_dump()
        u_dict["role"] = u.assigned_role or "Pending"
        users_data.append(u_dict)
        
    return SuccessResponse(data={"users": users_data})
@router.get("/audit-logs", response_model=SuccessResponse)
async def get_audit_logs(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role(["Admin", "Portal Admin"]))
):
    """Get recent system audit logs."""
    try:
        stmt = select(AuditLog).order_by(desc(AuditLog.timestamp)).limit(limit)
        result = await db.execute(stmt)
        logs = result.scalars().all()
        
        logs_data = []
        for log in logs:
            logs_data.append({
                "id": str(log.id),
                "created_at": log.timestamp.isoformat() if log.timestamp else None,
                "action": log.action,
                "resource": log.resource,
                "entity_type": log.entity_type if hasattr(log, "entity_type") else "System",
                "actor_id": log.user_id,
                "details": log.details
            })
            
        return SuccessResponse(data={"logs": logs_data})
    except Exception as e:
        logger.error(f"Failed to fetch audit logs: {str(e)}")
        return SuccessResponse(data={"logs": []})
