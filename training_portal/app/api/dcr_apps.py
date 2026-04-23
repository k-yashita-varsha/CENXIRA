import uuid
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import List

from app.database import get_db, RegisteredApp
from app.api.auth import get_current_user
from app.models import User

router = APIRouter()

class AppRegistrationRequest(BaseModel):
    name: str
    redirect_uris: List[str]
    base_url: str

class AppResponse(BaseModel):
    id: str
    name: str
    base_url: str
    status: str
    client_id: str | None = None

    class Config:
        orm_mode = True

@router.post("/register")
async def register_app(req: AppRegistrationRequest, db: AsyncSession = Depends(get_db)):
    # Check if exists
    stmt = select(RegisteredApp).where(RegisteredApp.name == req.name)
    result = await db.execute(stmt)
    existing = result.scalars().first()
    
    if existing:
        return {"status": existing.status, "message": "App already registered."}

    new_app = RegisteredApp(
        name=req.name,
        redirect_uris=req.redirect_uris,
        base_url=req.base_url,
        status="PENDING"
    )
    db.add(new_app)
    await db.commit()
    return {"status": "PENDING", "message": "App registered successfully. Waiting for Admin approval."}

@router.get("/status/{name}")
async def get_app_status(name: str, db: AsyncSession = Depends(get_db)):
    stmt = select(RegisteredApp).where(RegisteredApp.name == name)
    result = await db.execute(stmt)
    app = result.scalars().first()
    
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
        
    if app.status == "APPROVED":
        return {
            "status": "APPROVED",
            "client_id": app.client_id,
            "client_secret": app.client_secret
        }
    return {"status": app.status}

@router.get("/features", response_model=List[AppResponse])
async def get_features(db: AsyncSession = Depends(get_db)):
    stmt = select(RegisteredApp).where(RegisteredApp.status == "APPROVED")
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/", response_model=List[AppResponse])
async def get_all_apps(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.assigned_role != "Manager": # Manager acts as Admin in CENRIXA
        raise HTTPException(status_code=403, detail="Not authorized")
        
    stmt = select(RegisteredApp)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/{app_id}/approve")
async def approve_app(app_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.assigned_role != "Manager":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    stmt = select(RegisteredApp).where(RegisteredApp.id == uuid.UUID(app_id))
    result = await db.execute(stmt)
    app = result.scalars().first()
    
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
        
    if app.status == "APPROVED":
        return {"message": "Already approved"}

    # Mock DCR generation for robust testing, since we don't know the exact Keycloak URL or if it's running.
    # In production, this would make an httpx.post() to Keycloak's DCR endpoint.
    generated_client_id = f"client_{uuid.uuid4().hex[:8]}"
    generated_client_secret = uuid.uuid4().hex
    
    app.status = "APPROVED"
    app.client_id = generated_client_id
    app.client_secret = generated_client_secret
    
    await db.commit()
    return {"message": "App approved successfully", "client_id": app.client_id}
