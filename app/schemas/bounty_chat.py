from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


# Chat Schemas
class BountyChatResponse(BaseModel):
    id: UUID
    bounty_id: Optional[UUID]  # Deprecated, kept for compatibility
    client_id: UUID
    artist_id: Optional[UUID]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime]
    
    # User information (NEW - required by frontend)
    client_username: Optional[str] = None
    artist_username: Optional[str] = None
    client_avatar: Optional[str] = None
    artist_avatar: Optional[str] = None
    
    # Bounty context
    bounty_title: Optional[str] = None
    last_message_preview: Optional[str] = None
    
    # Additional info
    unread_count: int = 0
    
    class Config:
        from_attributes = True


# Message Schemas
class MessageCreate(BaseModel):
    message_type: str = Field(..., description="Type: text, image, voice, link, file")
    content: Optional[str] = Field(None, description="Text content or URL")
    bounty_id: Optional[UUID] = Field(None, description="Bounty context for this message")
    reply_to_id: Optional[UUID] = Field(None, description="ID of message being replied to")


class MessageUpdate(BaseModel):
    content: str = Field(..., description="Updated text content")


class AttachmentResponse(BaseModel):
    id: UUID
    file_url: str
    file_name: str
    file_size: int
    file_type: str
    thumbnail_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    order: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: UUID
    chat_id: UUID
    sender_id: UUID
    bounty_id: Optional[UUID]  # Context: which bounty this message is about
    message_type: str
    content: Optional[str]
    file_url: Optional[str]
    file_name: Optional[str]
    file_size: Optional[int]
    file_type: Optional[str]
    voice_duration: Optional[int]
    thumbnail_url: Optional[str]
    reply_to_id: Optional[UUID]
    is_edited: bool
    is_deleted: bool
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    # Additional info
    sender_username: Optional[str] = None
    sender_avatar: Optional[str] = None
    bounty_title: Optional[str] = None  # Title of the bounty for context
    attachments: List[AttachmentResponse] = []
    reply_to_message: Optional['MessageResponse'] = None
    
    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    messages: List[MessageResponse]
    total: int
    page: int
    limit: int
    has_more: bool


class ChatListResponse(BaseModel):
    chats: List[BountyChatResponse]
    total: int


class UnreadCountResponse(BaseModel):
    chat_id: UUID
    unread_count: int


class MarkAsReadRequest(BaseModel):
    message_ids: List[UUID] = Field(..., description="List of message IDs to mark as read")


class TypingStatusRequest(BaseModel):
    is_typing: bool = Field(..., description="Whether user is typing")


class TypingStatusResponse(BaseModel):
    user_id: UUID
    username: str
    is_typing: bool
    timestamp: datetime
