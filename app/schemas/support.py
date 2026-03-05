from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class SupportTicketCreate(BaseModel):
    subject: str
    category: str  # Payment, Technical, Account, Refund
    priority: str = "medium"  # low, medium, high
    message: str


class SupportTicketResponse(BaseModel):
    id: UUID
    user_id: UUID
    subject: str
    category: str
    priority: str
    status: str
    assigned_to: Optional[str]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True


class SupportMessageCreate(BaseModel):
    content: str
    attachments: List[str] = []


class SupportMessageResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    sender_id: UUID
    sender_type: str
    content: str
    attachments: List[str]
    created_at: datetime

    class Config:
        from_attributes = True


class SupportTicketWithMessages(BaseModel):
    id: UUID
    user_id: UUID
    subject: str
    category: str
    priority: str
    status: str
    assigned_to: Optional[str]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]
    messages: List[SupportMessageResponse] = []

    class Config:
        from_attributes = True


class TicketStatusUpdate(BaseModel):
    status: str  # pending, active, resolved


class TicketAssignUpdate(BaseModel):
    assigned_to: str


class FAQResponse(BaseModel):
    id: UUID
    category: str
    question: str
    answer: str
    order: int
    is_active: bool
    views: int
    helpful_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class FAQCreate(BaseModel):
    category: str
    question: str
    answer: str
    order: int = 0


class FAQUpdate(BaseModel):
    category: Optional[str] = None
    question: Optional[str] = None
    answer: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None
