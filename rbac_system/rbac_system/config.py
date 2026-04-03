"""
RBAC Configuration Module

Loads RBAC settings from environment variables.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class RBACConfig(BaseSettings):
    """
    RBAC configuration loaded from environment variables.
    
    Attributes:
        rbac_strict_mode: Enforce RBAC on all operations (True/False)
    """

    rbac_strict_mode: bool = Field(
        default=True,
        description="Enforce RBAC checks strictly",
        alias="RBAC_STRICT_MODE"
    )

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
        "case_sensitive": False
    }