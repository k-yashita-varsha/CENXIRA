from dotenv import load_dotenv
load_dotenv()  # Must be first — populates os.environ for all os.getenv() calls app-wide

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.database import init_db, close_db
from app.config import AppConfig

logger = logging.getLogger(__name__)

config = AppConfig()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for the FastAPI application."""
    logger.info("Starting up application...")
    
    # Initialize database tables
    await init_db()
    
    # Initialize RBAC Permission Checker
    from rbac_system.repository import SQLAlchemyRBACRepository
    from rbac_system.engine import RBACEngine, PermissionChecker
    from rbac_system.fastapi_utils import set_permission_checker
    from app.database import sync_engine as db_sync_engine
    
    repo = SQLAlchemyRBACRepository(db_sync_engine)
    rbac_engine = RBACEngine(repo)
    checker = PermissionChecker(repo)
    set_permission_checker(checker)
    logger.info("RBAC permission checker initialized")
    
    yield
    
    logger.info("Shutting down application...")
    # Close database connections
    await close_db()

# Create FastAPI application
app = FastAPI(
    title=config.app_name,
    version="1.0.0",
    description="CENRIXA Full-stack Training Management System",
    lifespan=lifespan,
    docs_url="/docs" if config.app_debug else None,
    redoc_url="/redoc" if config.app_debug else None,
)

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins if isinstance(config.cors_origins, list) else [config.cors_origins, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router, prefix=config.api_v1_str)

@app.get("/health", tags=["Health Check"])
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "app": config.app_name, "version": "1.0.0"}
