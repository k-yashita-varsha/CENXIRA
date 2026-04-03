import os
from pydantic_settings import BaseSettings

class AppConfig(BaseSettings):
    """Application Configuration Settings"""
    
    app_name: str = "CENRIXA Training Portal"
    app_debug: bool = True
    api_v1_str: str = "/api/v1"
    
    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]
    
    # Database
    database_url: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://postgres:postgres@localhost:5432/cenrixa_db"
    )
    
    @property
    def sync_database_url(self) -> str:
        """Get synchronous version of database URL."""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    # Keycloak Admin Credentials
    keycloak_url: str = os.getenv("KEYCLOAK_URL", "http://localhost:8080/")
    keycloak_realm: str = os.getenv("KEYCLOAK_REALM", "training-portal")
    keycloak_client_id: str = os.getenv("KEYCLOAK_CLIENT_ID", "portal-admin")
    keycloak_client_secret: str = os.getenv("KEYCLOAK_CLIENT_SECRET", "super-secret")
    
    # SMTP Settings
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", 587))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_pass: str = os.getenv("SMTP_PASS", "")

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
        "case_sensitive": False
    }
