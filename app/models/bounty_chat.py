from typing import Optional, List
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy import CheckConstraint


class BountyChat(SQLModel, table=True):
    """Chat between two users (client and artist) - shared across all their bounties"""
    __tablename__ = "bounty_chats"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    bounty_id: Optional[UUID] = Field(default=None, foreign_key="bounties.id", index=True)  # Deprecated, kept for compatibility
    client_id: UUID = Field(foreign_key="users.id", index=True)
    artist_id: Optional[UUID] = Field(default=None, foreign_key="users.id", index=True)
    
    # Status
    is_active: bool = Field(default=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_message_at: Optional[datetime] = None


class BountyChatMessage(SQLModel, table=True):
    """Individual messages in a bounty chat"""
    __tablename__ = "bounty_chat_messages"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    chat_id: UUID = Field(foreign_key="bounty_chats.id", index=True)
    sender_id: UUID = Field(foreign_key="users.id", index=True)
    bounty_id: Optional[UUID] = Field(default=None, foreign_key="bounties.id", index=True)  # Context: which bounty this message is about
    
    # Message content
    message_type: str = Field(max_length=20)  # 'text', 'image', 'voice', 'link', 'file'
    content: Optional[str] = None  # Text message or URL
    
    # File attachments
    file_url: Optional[str] = Field(default=None, max_length=500)
    file_name: Optional[str] = Field(default=None, max_length=255)
    file_size: Optional[int] = None  # Size in bytes
    file_type: Optional[str] = Field(default=None, max_length=50)  # MIME type
    
    # Voice note specific
    voice_duration: Optional[int] = None  # Duration in seconds
    
    # Image specific
    thumbnail_url: Optional[str] = Field(default=None, max_length=500)
    
    # Message metadata
    reply_to_id: Optional[UUID] = Field(default=None, foreign_key="bounty_chat_messages.id")
    is_edited: bool = Field(default=False)
    is_deleted: bool = Field(default=False)
    
    # Read status
    is_read: bool = Field(default=False)
    read_at: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint(
            "message_type IN ('text', 'image', 'voice', 'link', 'file')",
            name="valid_message_type"
        ),
    )


class BountyChatAttachment(SQLModel, table=True):
    """Multiple attachments for a single message"""
    __tablename__ = "bounty_chat_attachments"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    message_id: UUID = Field(foreign_key="bounty_chat_messages.id", index=True)
    
    # Attachment details
    file_url: str = Field(max_length=500)
    file_name: str = Field(max_length=255)
    file_size: int  # Size in bytes
    file_type: str = Field(max_length=50)  # MIME type
    
    # Image specific
    thumbnail_url: Optional[str] = Field(default=None, max_length=500)
    width: Optional[int] = None
    height: Optional[int] = None
    
    # Order
    order: int = Field(default=0)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
