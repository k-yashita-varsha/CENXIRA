from fastapi import APIRouter
from app.api.auth import router as auth_router
from app.api.admin import router as admin_router
from app.api.manager import router as manager_router
from app.api.trainee import router as trainee_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(manager_router)
api_router.include_router(trainee_router)
