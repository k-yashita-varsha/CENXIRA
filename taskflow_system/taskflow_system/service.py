"""
Taskflow Service Module

Core business logic for task management, state transitions, and validation.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from taskflow_system.config import TaskflowConfig
from taskflow_system.models import (
    Task,
    Submission,
    AuditEvent,
    TaskStatus,
    Priority,
    RecurrencePattern,
    ReviewStatus,
    TaskNotFoundError,
    SubmissionNotFoundError,
    InvalidTransitionError,
    TaskAlreadyAssignedError,
    TaskNotAssignedError,
    NoActiveSubmissionError,
    ValidationError,
    UnauthorizedError,
)

logger = logging.getLogger(__name__)


class TaskValidator:
    """
    Task validation utility.
    
    Validates task data before creation and updates.
    """

    @staticmethod
    def validate_task_name(name: str) -> bool:
        """Validate task name."""
        if not name or len(name) < 3:
            raise ValidationError("Task name must be at least 3 characters")
        if len(name) > 255:
            raise ValidationError("Task name cannot exceed 255 characters")
        return True

    @staticmethod
    def validate_priority(priority: str) -> bool:
        """Validate priority."""
        if priority not in [p.value for p in Priority]:
            raise ValidationError(f"Invalid priority: {priority}")
        return True

    @staticmethod
    def validate_status(status: str) -> bool:
        """Validate task status."""
        if status not in [s.value for s in TaskStatus]:
            raise ValidationError(f"Invalid status: {status}")
        return True

    @staticmethod
    def validate_due_date(due_date: Optional[datetime]) -> bool:
        """Validate due date."""
        if due_date and due_date < datetime.now():
            raise ValidationError("Due date cannot be in the past")
        return True

    @staticmethod
    def validate_recurrence(is_recurring: bool, pattern: str) -> bool:
        """Validate recurrence settings."""
        if is_recurring:
            if pattern not in [p.value for p in RecurrencePattern]:
                raise ValidationError(f"Invalid recurrence pattern: {pattern}")
        return True

    @staticmethod
    def validate_task_data(task_dict: Dict[str, Any]) -> bool:
        """Validate complete task data."""
        if "name" in task_dict:
            TaskValidator.validate_task_name(task_dict["name"])
        if "priority" in task_dict:
            TaskValidator.validate_priority(task_dict["priority"])
        if "status" in task_dict:
            TaskValidator.validate_status(task_dict["status"])
        if "due_date" in task_dict:
            TaskValidator.validate_due_date(task_dict.get("due_date"))
        if "is_recurring" in task_dict:
            TaskValidator.validate_recurrence(
                task_dict["is_recurring"],
                task_dict.get("recurrence_pattern", "ONCE")
            )
        return True


class TaskStateMachine:
    """
    Task status state machine.
    
    Manages valid state transitions for task workflow.
    Valid transitions:
    - BACKLOG → IN_PROGRESS
    - IN_PROGRESS → UNDER_REVIEW
    - UNDER_REVIEW → IN_PROGRESS (rejected)
    - UNDER_REVIEW → COMPLETED (approved)
    """

    # Valid transitions: {from_status: [to_statuses]}
    VALID_TRANSITIONS = {
        TaskStatus.BACKLOG: [TaskStatus.IN_PROGRESS],
        TaskStatus.IN_PROGRESS: [TaskStatus.UNDER_REVIEW, TaskStatus.BACKLOG],
        TaskStatus.UNDER_REVIEW: [TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS],
        TaskStatus.COMPLETED: [],  # Terminal state
    }

    @staticmethod
    def can_transition(current_status: str, target_status: str) -> bool:
        """Check if transition is valid."""
        return target_status in TaskStateMachine.VALID_TRANSITIONS.get(current_status, [])

    @staticmethod
    def validate_transition(current_status: str, target_status: str) -> bool:
        """Validate transition, raise if invalid."""
        if not TaskStateMachine.can_transition(current_status, target_status):
            raise InvalidTransitionError(current_status, target_status)
        return True


class TaskService:
    """
    Core task management service.
    
    Handles all task operations including creation, assignment, submission,
    and approval with full audit logging.
    """

    def __init__(self, repository: "TaskRepository", config: Optional[TaskflowConfig] = None):
        """
        Initialize task service.
        
        Args:
            repository: Task data repository
            config: TaskflowConfig instance
        """
        self.repository = repository
        self.config = config or TaskflowConfig()
        logger.info("TaskService initialized")

    # ==================== TASK CRUD ====================

    def create_task(
        self,
        name: str,
        created_by: str,
        description: str = "",
        priority: str = "MEDIUM",
        due_date: Optional[datetime] = None,
        is_recurring: bool = False,
        recurrence_pattern: str = "ONCE",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """
        Create a new task.
        
        Args:
            name: Task name
            created_by: User ID who created
            description: Task description
            priority: Priority level
            due_date: Due date
            is_recurring: Whether task recurs
            recurrence_pattern: Recurrence pattern
            metadata: Additional metadata
            
        Returns:
            Created Task
        """
        logger.info(f"Creating task: {name}")
        
        # Validate
        TaskValidator.validate_task_name(name)
        TaskValidator.validate_priority(priority)
        TaskValidator.validate_due_date(due_date)
        TaskValidator.validate_recurrence(is_recurring, recurrence_pattern)
        
        # Create
        task = Task(
            name=name,
            description=description,
            status=self.config.workflow_default_status,
            priority=priority,
            created_by=created_by,
            due_date=due_date,
            is_recurring=is_recurring,
            recurrence_pattern=recurrence_pattern,
            metadata=metadata or {},
        )
        
        saved = self.repository.save_task(task)
        
        # Audit
        if self.config.workflow_enable_audit:
            self.repository.log_audit(
                entity_type="task",
                entity_id=saved.id,
                action="create",
                actor=created_by,
                changes={}
            )
        
        logger.info(f"Task created: {saved.id}")
        return saved

    def get_task(self, task_id: str) -> Task:
        """Get task by ID."""
        return self.repository.get_task(task_id)

    def list_tasks(
        self,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> List[Task]:
        """List tasks with optional filters."""
        return self.repository.list_tasks(
            status=status,
            assigned_to=assigned_to,
            created_by=created_by
        )

    def update_task(
        self,
        task_id: str,
        updated_by: str,
        **updates
    ) -> Task:
        """
        Update task.
        
        Args:
            task_id: Task ID
            updated_by: User ID who updated
            **updates: Fields to update
            
        Returns:
            Updated Task
        """
        logger.info(f"Updating task: {task_id}")
        
        task = self.repository.get_task(task_id)
        original = dict(task.__dict__)
        
        # Validate updates
        TaskValidator.validate_task_data(updates)
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        task.updated_at = datetime.now()
        saved = self.repository.save_task(task)
        
        # Audit
        if self.config.workflow_enable_audit:
            changes = {k: {"old": original.get(k), "new": updates.get(k)}
                      for k in updates}
            self.repository.log_audit(
                entity_type="task",
                entity_id=task_id,
                action="update",
                actor=updated_by,
                changes=changes
            )
        
        logger.info(f"Task updated: {task_id}")
        return saved

    def delete_task(self, task_id: str, deleted_by: str) -> bool:
        """Delete task."""
        logger.info(f"Deleting task: {task_id}")
        self.repository.delete_task(task_id)
        
        if self.config.workflow_enable_audit:
            self.repository.log_audit(
                entity_type="task",
                entity_id=task_id,
                action="delete",
                actor=deleted_by,
                changes={}
            )
        
        logger.info(f"Task deleted: {task_id}")
        return True

    # ==================== TASK WORKFLOW ====================

    def assign_task(self, task_id: str, assigned_to: str, assigned_by: str) -> Task:
        """
        Assign task to user.
        
        Args:
            task_id: Task ID
            assigned_to: User ID to assign to
            assigned_by: User ID doing assignment
            
        Returns:
            Updated Task
        """
        logger.info(f"Assigning task {task_id} to {assigned_to}")
        
        task = self.repository.get_task(task_id)
        
        if task.assigned_to:
            raise TaskAlreadyAssignedError(task_id)
        
        task.assigned_to = assigned_to
        task.updated_at = datetime.now()
        saved = self.repository.save_task(task)
        
        if self.config.workflow_enable_audit:
            self.repository.log_audit(
                entity_type="task",
                entity_id=task_id,
                action="assign",
                actor=assigned_by,
                changes={"assigned_to": {"old": None, "new": assigned_to}}
            )
        
        logger.info(f"Task assigned: {task_id}")
        return saved

    def start_task(self, task_id: str, started_by: str) -> Task:
        """Start task (BACKLOG → IN_PROGRESS)."""
        logger.info(f"Starting task: {task_id}")
        
        task = self.repository.get_task(task_id)
        
        if not task.assigned_to:
            raise TaskNotAssignedError(task_id)
        
        TaskStateMachine.validate_transition(task.status, TaskStatus.IN_PROGRESS)
        
        task.status = TaskStatus.IN_PROGRESS
        task.updated_at = datetime.now()
        saved = self.repository.save_task(task)
        
        if self.config.workflow_enable_audit:
            self.repository.log_audit(
                entity_type="task",
                entity_id=task_id,
                action="start",
                actor=started_by,
                changes={"status": {"old": TaskStatus.BACKLOG, "new": TaskStatus.IN_PROGRESS}}
            )
        
        logger.info(f"Task started: {task_id}")
        return saved

    def submit_task(self, task_id: str, submitted_by: str, notes: str = "") -> Submission:
        """
        Submit task (create submission).
        
        Args:
            task_id: Task ID
            submitted_by: User ID submitting
            notes: Submission notes
            
        Returns:
            Created Submission
        """
        logger.info(f"Submitting task: {task_id}")
        
        task = self.repository.get_task(task_id)
        TaskStateMachine.validate_transition(task.status, TaskStatus.UNDER_REVIEW)
        
        # Create submission
        submission = Submission(
            task_id=task_id,
            submitted_by=submitted_by,
            notes=notes,
        )
        saved = self.repository.save_submission(submission)
        
        # Update task status
        task.status = TaskStatus.UNDER_REVIEW
        task.updated_at = datetime.now()
        self.repository.save_task(task)
        
        if self.config.workflow_enable_audit:
            self.repository.log_audit(
                entity_type="submission",
                entity_id=saved.id,
                action="create",
                actor=submitted_by,
                changes={}
            )
        
        logger.info(f"Task submitted: {task_id}")
        return saved

    def approve_submission(
        self,
        submission_id: str,
        approved_by: str,
        comments: str = ""
    ) -> Submission:
        """
        Approve submission (mark task COMPLETED).
        
        Args:
            submission_id: Submission ID
            approved_by: Reviewer user ID
            comments: Review comments
            
        Returns:
            Updated Submission
        """
        logger.info(f"Approving submission: {submission_id}")
        
        submission = self.repository.get_submission(submission_id)
        task = self.repository.get_task(submission.task_id)
        
        TaskStateMachine.validate_transition(task.status, TaskStatus.COMPLETED)
        
        # Update submission
        submission.review_status = ReviewStatus.APPROVED
        submission.reviewed_by = approved_by
        submission.reviewed_at = datetime.now()
        submission.review_comments = comments
        saved = self.repository.save_submission(submission)
        
        # Update task
        task.status = TaskStatus.COMPLETED
        task.updated_at = datetime.now()
        self.repository.save_task(task)
        
        if self.config.workflow_enable_audit:
            self.repository.log_audit(
                entity_type="submission",
                entity_id=submission_id,
                action="approve",
                actor=approved_by,
                changes={"review_status": {"old": ReviewStatus.PENDING, "new": ReviewStatus.APPROVED}}
            )
        
        logger.info(f"Submission approved: {submission_id}")
        return saved

    def reject_submission(
        self,
        submission_id: str,
        rejected_by: str,
        comments: str = ""
    ) -> Submission:
        """
        Reject submission (return to IN_PROGRESS).
        
        Args:
            submission_id: Submission ID
            rejected_by: Reviewer user ID
            comments: Rejection comments
            
        Returns:
            Updated Submission
        """
        logger.info(f"Rejecting submission: {submission_id}")
        
        submission = self.repository.get_submission(submission_id)
        task = self.repository.get_task(submission.task_id)
        
        TaskStateMachine.validate_transition(task.status, TaskStatus.IN_PROGRESS)
        
        # Update submission
        submission.review_status = ReviewStatus.REJECTED
        submission.reviewed_by = rejected_by
        submission.reviewed_at = datetime.now()
        submission.review_comments = comments
        saved = self.repository.save_submission(submission)
        
        # Update task
        task.status = TaskStatus.IN_PROGRESS
        task.updated_at = datetime.now()
        self.repository.save_task(task)
        
        if self.config.workflow_enable_audit:
            self.repository.log_audit(
                entity_type="submission",
                entity_id=submission_id,
                action="reject",
                actor=rejected_by,
                changes={"review_status": {"old": ReviewStatus.PENDING, "new": ReviewStatus.REJECTED}}
            )
        
        logger.info(f"Submission rejected: {submission_id}")
        return saved

    # ==================== RECURRING TASKS ====================

    def get_due_recurring_tasks(self) -> List[Task]:
        """Get recurring tasks that are due for execution."""
        return self.repository.get_due_recurring_tasks()

    def execute_recurring_task(self, task_id: str, executed_by: str) -> Task:
        """Execute recurring task (create new instance)."""
        logger.info(f"Executing recurring task: {task_id}")
        
        task = self.repository.get_task(task_id)
        
        if not task.is_recurring:
            raise ValidationError(f"Task is not recurring: {task_id}")
        
        # Update last run
        task.recurrence_last_run = datetime.now()
        self.repository.save_task(task)
        
        logger.info(f"Recurring task executed: {task_id}")
        return task