from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.services.bounty_chat_service import BountyChatService
from app.schemas.bounty_chat import (
    BountyChatResponse, MessageCreate, MessageUpdate, MessageResponse,
    MessageListResponse, ChatListResponse, UnreadCountResponse,
    MarkAsReadRequest
)

router = APIRouter()


@router.get("/my-chats", response_model=ChatListResponse)
async def get_my_chats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all chats for current user"""
    service = BountyChatService(db)
    return await service.get_user_chats(current_user.id)


@router.get("/bounty/{bounty_id}", response_model=BountyChatResponse)
async def get_bounty_chat(
    bounty_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get or create chat for a bounty"""
    service = BountyChatService(db)
    return await service.get_or_create_chat(bounty_id, current_user.id)


@router.get("/bounty/{bounty_id}/messages", response_model=MessageListResponse)
async def get_chat_messages(
    bounty_id: UUID,
    page: int = 1,
    limit: int = 50,
    before_message_id: Optional[UUID] = None,
    filter_by_bounty: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get messages for a bounty chat with pagination
    
    - filter_by_bounty: If True, only show messages for this specific bounty
    - If False (default), show all messages in the conversation (across all bounties)
    """
    service = BountyChatService(db)
    return await service.get_messages(
        bounty_id=bounty_id,
        user_id=current_user.id,
        page=page,
        limit=limit,
        before_message_id=before_message_id,
        filter_by_bounty=filter_by_bounty
    )


@router.post("/bounty/{bounty_id}/messages/text", response_model=MessageResponse)
async def send_text_message(
    bounty_id: UUID,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a text or link message"""
    service = BountyChatService(db)
    return await service.send_text_message(bounty_id, current_user.id, message_data)


@router.post("/bounty/{bounty_id}/messages/image", response_model=MessageResponse)
async def send_image_message(
    bounty_id: UUID,
    image: UploadFile = File(..., description="Image file"),
    caption: Optional[str] = Form(None, description="Optional caption"),
    reply_to_id: Optional[str] = Form(None, description="Message ID to reply to"),
    message_bounty_id: Optional[str] = Form(None, description="Bounty context for this message (defaults to current bounty)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send an image message with optional bounty context"""
    service = BountyChatService(db)
    
    # Convert string UUIDs to UUID objects
    reply_uuid = UUID(reply_to_id) if reply_to_id else None
    bounty_uuid = UUID(message_bounty_id) if message_bounty_id else None
    
    return await service.send_image_message(
        bounty_id=bounty_id,
        user_id=current_user.id,
        image_file=image,
        caption=caption,
        reply_to_id=reply_uuid,
        message_bounty_id=bounty_uuid
    )


@router.post("/bounty/{bounty_id}/messages/voice", response_model=MessageResponse)
async def send_voice_message(
    bounty_id: UUID,
    voice: UploadFile = File(..., description="Voice note file"),
    duration: Optional[int] = Form(None, description="Duration in seconds"),
    reply_to_id: Optional[str] = Form(None, description="Message ID to reply to"),
    message_bounty_id: Optional[str] = Form(None, description="Bounty context for this message (defaults to current bounty)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a voice note message with optional bounty context"""
    service = BountyChatService(db)
    
    # Convert string UUIDs to UUID objects
    reply_uuid = UUID(reply_to_id) if reply_to_id else None
    bounty_uuid = UUID(message_bounty_id) if message_bounty_id else None
    
    return await service.send_voice_message(
        bounty_id=bounty_id,
        user_id=current_user.id,
        voice_file=voice,
        duration=duration,
        reply_to_id=reply_uuid,
        message_bounty_id=bounty_uuid
    )


@router.put("/messages/{message_id}", response_model=MessageResponse)
async def update_message(
    message_id: UUID,
    message_data: MessageUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a text message"""
    service = BountyChatService(db)
    return await service.update_message(message_id, current_user.id, message_data)


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a message"""
    service = BountyChatService(db)
    return await service.delete_message(message_id, current_user.id)


@router.post("/bounty/{bounty_id}/mark-read")
async def mark_messages_as_read(
    bounty_id: UUID,
    request: MarkAsReadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark messages as read"""
    service = BountyChatService(db)
    return await service.mark_as_read(bounty_id, current_user.id, request.message_ids)


@router.get("/bounty/{bounty_id}/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    bounty_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get unread message count for a bounty chat"""
    service = BountyChatService(db)
    return await service.get_unread_count(bounty_id, current_user.id)
