from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field


class AdminAction(SQLModel, table=True):
    __tablename__ = "admin_actions"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    admin_id: UUID = Field(foreign_key="users.id")
    action_type: str  # model_approved, user_banned, etc.
    target_type: str  # model, user, community, etc.
    target_id: UUID
    details: str = Field(default="{}")  # JSON
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ContentReport(SQLModel, table=True):
    __tablename__ = "content_reports"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    reporter_id: UUID = Field(foreign_key="users.id")
    content_type: str  # post, model, comment
    content_id: UUID
    reason: str
    status: str = Field(default="pending")  # pending, resolved, dismissed
    created_at: datetime = Field(default_factory=datetime.utcnow)
