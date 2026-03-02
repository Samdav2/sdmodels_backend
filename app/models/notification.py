from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field


class Notification(SQLModel, table=True):
    __tablename__ = "notifications"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    type: str  # like, comment, purchase, follow, etc.
    title: str
    message: str
    link: Optional[str] = None
    related_id: Optional[UUID] = None  # ID of related entity (model, bounty, transaction, etc.)
    related_title: Optional[str] = None  # Title of related entity
    is_read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
