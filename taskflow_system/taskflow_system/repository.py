"""
Taskflow Repository Module

Abstract repository interface for task operations.
Implementations can use any database (SQL, NoSQL, etc).
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import logging

from taskflow_system.models import (
    Task,
    Submission,
    AuditEvent,
    TaskNotFoundError,
    SubmissionNotFoundError,
)

logger = logging.getLogger(__name__)


class TaskRepository(ABC):
    """
    Abstract Task Repository.
    
    Defines interface for task data operations.
    Implement this interface with your database technology.
    
    Example implementations:
    - SQLAlchemyTaskRepository (PostgreSQL, MySQL, SQLite)
    - MongoDBTaskRepository
    - FirestoreTaskRepository
    """

    # ==================== TASK OPERATIONS ====================

    @abstractmethod
    def save_task(self, task: Task) -> Task:
        """Save task to database."""
        pass

    @abstractmethod
    def get_task(self, task_id: str) -> Task:
        """Get task by ID. Raise TaskNotFoundError if not found."""
        pass

    @abstractmethod
    def delete_task(self, task_id: str) -> bool:
        """Delete task."""
        pass

    @abstractmethod
    def list_tasks(
        self,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> List[Task]:
        """List tasks with optional filters."""
        pass

    # ==================== SUBMISSION OPERATIONS ====================

    @abstractmethod
    def save_submission(self, submission: Submission) -> Submission:
        """Save submission to database."""
        pass

    @abstractmethod
    def get_submission(self, submission_id: str) -> Submission:
        """Get submission by ID. Raise SubmissionNotFoundError if not found."""
        pass

    @abstractmethod
    def delete_submission(self, submission_id: str) -> bool:
        """Delete submission."""
        pass

    @abstractmethod
    def list_submissions(self, task_id: str) -> List[Submission]:
        """List submissions for a task."""
        pass

    # ==================== RECURRING TASKS ====================

    @abstractmethod
    def get_due_recurring_tasks(self) -> List[Task]:
        """Get recurring tasks that are due for execution."""
        pass

    # ==================== AUDIT LOGGING ====================

    @abstractmethod
    def log_audit(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        actor: str,
        changes: dict,
    ) -> AuditEvent:
        """Log audit event."""
        pass

    @abstractmethod
    def get_audit_logs(self, entity_type: str, entity_id: str) -> List[AuditEvent]:
        """Get audit logs for entity."""
        pass


class AuditLogger:
    """
    Audit logging utility.
    
    Provides convenient methods for audit logging.
    """

    def __init__(self, repository: TaskRepository):
        """
        Initialize audit logger.
        
        Args:
            repository: Task repository implementation
        """
        self.repository = repository

    def log_task_creation(self, task_id: str, created_by: str) -> AuditEvent:
        """Log task creation."""
        return self.repository.log_audit(
            entity_type="task",
            entity_id=task_id,
            action="create",
            actor=created_by,
            changes={}
        )

    def log_task_update(
        self,
        task_id: str,
        updated_by: str,
        changes: dict
    ) -> AuditEvent:
        """Log task update."""
        return self.repository.log_audit(
            entity_type="task",
            entity_id=task_id,
            action="update",
            actor=updated_by,
            changes=changes
        )

    def log_task_status_change(
        self,
        task_id: str,
        old_status: str,
        new_status: str,
        changed_by: str
    ) -> AuditEvent:
        """Log task status change."""
        return self.repository.log_audit(
            entity_type="task",
            entity_id=task_id,
            action="status_change",
            actor=changed_by,
            changes={"status": {"old": old_status, "new": new_status}}
        )

    def log_submission(self, submission_id: str, submitted_by: str) -> AuditEvent:
        """Log submission creation."""
        return self.repository.log_audit(
            entity_type="submission",
            entity_id=submission_id,
            action="create",
            actor=submitted_by,
            changes={}
        )

    def log_submission_review(
        self,
        submission_id: str,
        review_status: str,
        reviewed_by: str
    ) -> AuditEvent:
        """Log submission review."""
        return self.repository.log_audit(
            entity_type="submission",
            entity_id=submission_id,
            action="review",
            actor=reviewed_by,
            changes={"review_status": {"old": "PENDING", "new": review_status}}
        )

    def get_task_audit_logs(self, task_id: str) -> List[AuditEvent]:
        """Get all audit logs for task."""
        return self.repository.get_audit_logs("task", task_id)

    def get_submission_audit_logs(self, submission_id: str) -> List[AuditEvent]:
        """Get all audit logs for submission."""
        return self.repository.get_audit_logs("submission", submission_id)