from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


# Request Schemas

class TicketStatusUpdateAdmin(BaseModel):
    status: str  # pending, active, resolved, closed
    notes: Optional[str] = None


class TicketAssignmentUpdate(BaseModel):
    assigned_to: Optional[UUID] = None
    notes: Optional[str] = None


class TicketPriorityUpdate(BaseModel):
    priority: str  # low, medium, high, urgent
    notes: Optional[str] = None


class InternalNoteCreate(BaseModel):
    content: str
    attachments: List[str] = []


class AdminResponseCreate(BaseModel):
    content: str
    attachments: List[str] = []
    update_status: Optional[str] = None  # Optionally update status when responding


class BulkUpdateRequest(BaseModel):
    ticket_ids: List[UUID]
    action: str  # assign, status, priority, add_tag, remove_tag
    value: str  # Value depends on action
    notes: Optional[str] = None


class TicketTagsUpdate(BaseModel):
    action: str  # add or remove
    tags: List[str]


class CannedResponseCreate(BaseModel):
    title: str
    content: str
    category: Optional[str] = None
    shortcut: Optional[str] = None


class CannedResponseUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    shortcut: Optional[str] = None


# Response Schemas

class UserBasicInfo(BaseModel):
    id: UUID
    email: str
    username: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    
    class Config:
        from_attributes = True


class AdminBasicInfo(BaseModel):
    id: UUID
    username: str
    full_name: Optional[str]
    
    class Config:
        from_attributes = True


class TicketListItem(BaseModel):
    id: UUID
    user_id: UUID
    user_email: Optional[str]
    user_name: Optional[str]
    subject: str
    category: str
    priority: str
    status: str
    assigned_to: Optional[UUID]
    assigned_to_name: Optional[str]
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime
    first_response_at: Optional[datetime]
    sla_breach: bool = False
    unread_messages: int = 0
    
    class Config:
        from_attributes = True


class AdminTicketListResponse(BaseModel):
    tickets: List[TicketListItem]
    total: int
    page: int
    limit: int
    total_pages: int


class MessageDetail(BaseModel):
    id: UUID
    sender_id: UUID
    sender_type: str
    sender_name: Optional[str]
    sender_avatar: Optional[str]
    content: str
    attachments: List[str]
    is_internal: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True


class TicketHistoryItem(BaseModel):
    id: UUID
    admin_id: UUID
    admin_name: Optional[str]
    action: str
    old_value: Optional[str]
    new_value: Optional[str]
    notes: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AdminTicketDetailResponse(BaseModel):
    id: UUID
    user_id: UUID
    user: UserBasicInfo
    subject: str
    category: str
    priority: str
    status: str
    assigned_to: Optional[UUID]
    assigned_admin: Optional[AdminBasicInfo]
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]
    closed_at: Optional[datetime]
    first_response_at: Optional[datetime]
    sla_breach: bool = False
    satisfaction_rating: Optional[int]
    satisfaction_comment: Optional[str]
    messages: List[MessageDetail]
    history: List[TicketHistoryItem]


class OverviewStats(BaseModel):
    total_tickets: int
    pending: int
    active: int
    resolved: int
    closed: int


class CategoryStats(BaseModel):
    Payment: int = 0
    Technical: int = 0
    Account: int = 0
    Refund: int = 0
    General: int = 0


class PriorityStats(BaseModel):
    low: int = 0
    medium: int = 0
    high: int = 0
    urgent: int = 0


class SLAMetrics(BaseModel):
    average_first_response_time: str
    average_resolution_time: str
    sla_breach_count: int
    sla_compliance_rate: str


class SatisfactionStats(BaseModel):
    average_rating: float
    total_ratings: int
    rating_distribution: Dict[str, int]


class AdminPerformance(BaseModel):
    admin_id: UUID
    admin_name: str
    tickets_handled: int
    average_response_time: str
    average_resolution_time: str
    satisfaction_rating: float


class AdminSupportStats(BaseModel):
    overview: OverviewStats
    by_category: CategoryStats
    by_priority: PriorityStats
    sla_metrics: SLAMetrics
    satisfaction: SatisfactionStats
    admin_performance: List[AdminPerformance]


class CannedResponseResponse(BaseModel):
    id: UUID
    title: str
    content: str
    category: Optional[str]
    shortcut: Optional[str]
    usage_count: int
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
