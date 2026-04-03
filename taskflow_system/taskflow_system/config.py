"""
Taskflow Configuration Module

Loads taskflow settings from environment variables.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class TaskflowConfig(BaseSettings):
    """
    Taskflow configuration loaded from environment variables.
    
    Attributes:
        workflow_default_status: Default task status (default: PENDING)
        workflow_enable_audit: Enable audit logging (default: True)
        workflow_strict_transitions: Enforce valid state transitions (default: True)
        scheduler_interval_seconds: Recurring task check interval (default: 60)
    """

    workflow_default_status: str = Field(
        default="PENDING",
        description="Default task status",
        alias="WORKFLOW_DEFAULT_STATUS"
    )

    workflow_enable_audit: bool = Field(
        default=True,
        description="Enable audit logging",
        alias="WORKFLOW_ENABLE_AUDIT"
    )

    workflow_strict_transitions: bool = Field(
        default=True,
        description="Enforce strict state transitions",
        alias="WORKFLOW_STRICT_TRANSITIONS"
    )

    scheduler_interval_seconds: int = Field(
        default=60,
        description="Recurring task scheduler interval (seconds)",
        alias="SCHEDULER_INTERVAL_SECONDS"
    )

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
        "case_sensitive": False
    }