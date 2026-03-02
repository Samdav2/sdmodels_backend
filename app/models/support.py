from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field


class SupportTicket(SQLModel, table=True):
    __tablename__ = "support_tickets"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    subject: str
    category: str  # Payment, Technical, Account, Refund
    priority: str = Field(default="medium")  # low, medium, high
    status: str = Field(default="pending")  # pending, active, resolved
    assigned_to: Optional[str] = None  # Admin Team, Support Team, etc.
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None


class SupportMessage(SQLModel, table=True):
    __tablename__ = "support_messages"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    ticket_id: UUID = Field(foreign_key="support_tickets.id")
    sender_id: UUID = Field(foreign_key="users.id")
    sender_type: str  # user, admin
    content: str
    attachments: str = Field(default="[]")  # JSON array of URLs
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FAQ(SQLModel, table=True):
    __tablename__ = "faqs"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    category: str  # Payment, Technical, Account, General
    question: str
    answer: str
    order: int = Field(default=0)  # Display order
    is_active: bool = Field(default=True)
    views: int = Field(default=0)
    helpful_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
