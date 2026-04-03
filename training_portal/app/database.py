"""
Database Models

SQLAlchemy ORM models for all 8 entities:
- User, Role, Permission, UserRole, RolePermission
- Task, Submission, AuditLog
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, ForeignKey, Table, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class TaskStatusConstants:
    """Task workflow status constants."""
    BACKLOG = "BACKLOG"
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    UNDER_REVIEW = "UNDER_REVIEW"
    COMPLETED = "COMPLETED"


class ReviewStatusConstants:
    """Submission review status constants."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# ==================== USER & RBAC MODELS ====================

class User(Base, TimestampMixin):
    """
    User model.
    
    Synced from Keycloak via keycloak_id.
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    keycloak_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(255), unique=True, nullable=False)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    ohr_id = Column(String(255), unique=True, nullable=True)  # Generated on approval
    assigned_role = Column(String(100), nullable=True)  # Admin, Manager, Trainee
    status = Column(String(50), default="PENDING", nullable=False)  # PENDING, ACTIVE, REJECTED
    is_enabled = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    roles = relationship(
        "Role", 
        secondary="user_roles", 
        primaryjoin="User.id == foreign(UserRole.user_id)",
        secondaryjoin="Role.id == foreign(UserRole.role_id)",
        back_populates="users"
    )
    tasks_created = relationship("Task", foreign_keys="Task.created_by", back_populates="creator")
    tasks_assigned = relationship("Task", foreign_keys="Task.assigned_to", back_populates="assignee")
    submissions = relationship("Submission", foreign_keys="Submission.submitted_by", back_populates="submitter")
    audit_logs = relationship("AuditLog", foreign_keys="AuditLog.actor_id", back_populates="actor")

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class Role(Base, TimestampMixin):
    """
    Role model.
    
    Dynamic roles defined at runtime.
    """
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, default=False, nullable=False)  # System roles can't be deleted
    
    # Relationships
    users = relationship(
        "User", 
        secondary="user_roles", 
        primaryjoin="Role.id == foreign(UserRole.role_id)",
        secondaryjoin="User.id == foreign(UserRole.user_id)",
        back_populates="roles"
    )
    permissions = relationship("Permission", secondary="role_permissions", back_populates="roles")

    def __repr__(self) -> str:
        return f"<Role {self.name}>"


class Permission(Base, TimestampMixin):
    """
    Permission model.
    
    Format: resource:action (e.g., "users:approve", "tasks:create")
    """
    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False, index=True)
    resource = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Relationships
    roles = relationship("Role", secondary="role_permissions", back_populates="permissions")

    def __repr__(self) -> str:
        return f"<Permission {self.name}>"


class UserRole(Base, TimestampMixin):
    """User to Role assignment."""
    __tablename__ = "user_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint('user_id', 'role_id', name='uq_user_role'),
    )


class RolePermission(Base, TimestampMixin):
    """Role to Permission assignment."""
    __tablename__ = "role_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    permission_id = Column(UUID(as_uuid=True), ForeignKey("permissions.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),
    )


# ==================== TASK MODELS ====================

class Task(Base, TimestampMixin):
    """
    Task model.
    
    Represents a training task in the workflow.
    """
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="PENDING", nullable=False, index=True)
    priority = Column(String(20), default="MEDIUM", nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    due_date = Column(DateTime, nullable=True)
    is_recurring = Column(Boolean, default=False, nullable=False)
    recurrence_pattern = Column(String(20), default="ONCE", nullable=False)
    recurrence_last_run = Column(DateTime, nullable=True)
    task_metadata = Column(JSONB, default={}, nullable=False)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by], back_populates="tasks_created")
    assignee = relationship("User", foreign_keys=[assigned_to], back_populates="tasks_assigned")
    submissions = relationship("Submission", back_populates="task")

    def __repr__(self) -> str:
        return f"<Task {self.name}>"


class Submission(Base, TimestampMixin):
    """
    Submission model.
    
    Represents task submission and review.
    """
    __tablename__ = "submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    submitted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    notes = Column(Text, nullable=True)
    file_references = Column(JSONB, default=[], nullable=False)
    links = Column(JSONB, default=[], nullable=False)
    review_status = Column(String(50), default="PENDING", nullable=False)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_comments = Column(Text, nullable=True)
    
    # Relationships
    task = relationship("Task", back_populates="submissions")
    submitter = relationship("User", foreign_keys=[submitted_by], back_populates="submissions")

    def __repr__(self) -> str:
        return f"<Submission {self.id}>"


# ==================== AUDIT LOG ====================

class AuditLog(Base, TimestampMixin):
    """
    Audit log model.
    
    Tracks all changes to tasks and submissions.
    """
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    changes = Column(JSONB, default={}, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    actor = relationship("User", foreign_keys=[actor_id], back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} on {self.entity_type}>"


# ==================== DATABASE SETUP ====================

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import AppConfig

config = AppConfig()

# Create async engine
engine = create_async_engine(
    config.database_url,
    echo=config.app_debug,
    future=True,
    pool_size=20,
    max_overflow=40,
)

from sqlalchemy import create_engine
sync_engine = create_engine(
    config.sync_database_url,
    echo=config.app_debug,
    future=True,
    pool_size=5,
    max_overflow=10,
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db():
    """Dependency for getting database session."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """Initialize database (create tables)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connection."""
    await engine.dispose()