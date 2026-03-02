from typing import Optional, List
from uuid import UUID
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.bounty_chat_repository import BountyChatRepository
from app.repositories.bounty_repository import BountyRepository
from app.schemas.bounty_chat import (
    BountyChatResponse, MessageCreate, MessageUpdate, MessageResponse,
    MessageListResponse, ChatListResponse, UnreadCountResponse,
    AttachmentResponse
)
from app.utils.file_utils import generate_secure_filename, get_file_extension, get_content_type
from app.utils.opendrive_storage import opendrive_storage
import json


class BountyChatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.chat_repo = BountyChatRepository(db)
        self.bounty_repo = BountyRepository(db)
    
    async def _enrich_message_response(self, message) -> MessageResponse:
        """Enrich message with user info, bounty context, and attachments"""
        # Get sender info
        sender_info = await self.chat_repo.get_user_info(message.sender_id)
        
        # Get bounty context if message has bounty_id
        bounty_title = None
        if message.bounty_id:
            bounty_info = await self.chat_repo.get_bounty_info(message.bounty_id)
            if bounty_info:
                bounty_title = bounty_info['title']
        
        # Handle deleted messages - replace content with placeholder
        content = message.content
        file_url = message.file_url
        file_name = message.file_name
        thumbnail_url = message.thumbnail_url
        attachments_list = []
        
        if message.is_deleted:
            # Replace content with placeholder for deleted messages
            content = "Message deleted"
            file_url = None
            file_name = None
            thumbnail_url = None
            # Don't show attachments for deleted messages
        else:
            # Get attachments only for non-deleted messages
            attachments = await self.chat_repo.get_message_attachments(message.id)
            attachments_list = [
                AttachmentResponse(
                    id=att.id,
                    file_url=att.file_url,
                    file_name=att.file_name,
                    file_size=att.file_size,
                    file_type=att.file_type,
                    thumbnail_url=att.thumbnail_url,
                    width=att.width,
                    height=att.height,
                    order=att.order,
                    created_at=att.created_at
                )
                for att in attachments
            ]
        
        # Get reply-to message if exists
        reply_to_message = None
        if message.reply_to_id:
            reply_msg = await self.chat_repo.get_message_by_id(message.reply_to_id)
            if reply_msg:
                reply_sender_info = await self.chat_repo.get_user_info(reply_msg.sender_id)
                # Handle deleted reply messages
                reply_content = "Message deleted" if reply_msg.is_deleted else reply_msg.content
                reply_file_url = None if reply_msg.is_deleted else reply_msg.file_url
                reply_file_name = None if reply_msg.is_deleted else reply_msg.file_name
                reply_thumbnail_url = None if reply_msg.is_deleted else reply_msg.thumbnail_url
                
                reply_to_message = MessageResponse(
                    id=reply_msg.id,
                    chat_id=reply_msg.chat_id,
                    sender_id=reply_msg.sender_id,
                    bounty_id=reply_msg.bounty_id,
                    message_type=reply_msg.message_type,
                    content=reply_content,
                    file_url=reply_file_url,
                    file_name=reply_file_name,
                    file_size=reply_msg.file_size,
                    file_type=reply_msg.file_type,
                    voice_duration=reply_msg.voice_duration,
                    thumbnail_url=reply_thumbnail_url,
                    reply_to_id=None,  # Don't nest further
                    is_edited=reply_msg.is_edited,
                    is_deleted=reply_msg.is_deleted,
                    is_read=reply_msg.is_read,
                    read_at=reply_msg.read_at,
                    created_at=reply_msg.created_at,
                    updated_at=reply_msg.updated_at,
                    sender_username=reply_sender_info['username'] if reply_sender_info else None,
                    sender_avatar=reply_sender_info['avatar'] if reply_sender_info else None,
                    bounty_title=None,
                    attachments=[]
                )
        
        return MessageResponse(
            id=message.id,
            chat_id=message.chat_id,
            sender_id=message.sender_id,
            bounty_id=message.bounty_id,
            message_type=message.message_type,
            content=content,
            file_url=file_url,
            file_name=file_name,
            file_size=message.file_size,
            file_type=message.file_type,
            voice_duration=message.voice_duration,
            thumbnail_url=thumbnail_url,
            reply_to_id=message.reply_to_id,
            is_edited=message.is_edited,
            is_deleted=message.is_deleted,
            is_read=message.is_read,
            read_at=message.read_at,
            created_at=message.created_at,
            updated_at=message.updated_at,
            sender_username=sender_info['username'] if sender_info else None,
            sender_avatar=sender_info['avatar'] if sender_info else None,
            bounty_title=bounty_title,
            attachments=attachments_list,
            reply_to_message=reply_to_message
        )
    
    async def get_or_create_chat(self, bounty_id: UUID, user_id: UUID) -> BountyChatResponse:
        """Get or create chat for a bounty (creates user-pair chat)"""
        # Get bounty to verify access and get the other user
        bounty = await self.bounty_repo.get_bounty(bounty_id)
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        
        # Verify user is client or artist
        if bounty.poster_id != user_id and bounty.claimed_by_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this chat"
            )
        
        # Determine the other user
        if not bounty.claimed_by_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bounty has not been claimed yet. No artist to chat with."
            )
        
        other_user_id = bounty.claimed_by_id if user_id == bounty.poster_id else bounty.poster_id
        
        # Get or create chat for this user pair
        chat = await self.chat_repo.get_or_create_chat(
            client_id=bounty.poster_id,
            artist_id=bounty.claimed_by_id
        )
        
        # Get unread count
        unread_count = await self.chat_repo.get_unread_count(chat.id, user_id)
        
        return BountyChatResponse(
            id=chat.id,
            bounty_id=bounty_id,  # Return the requested bounty_id for context
            client_id=chat.client_id,
            artist_id=chat.artist_id,
            is_active=chat.is_active,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            last_message_at=chat.last_message_at,
            unread_count=unread_count
        )
    
    async def get_user_chats(self, user_id: UUID) -> ChatListResponse:
        """Get all chats for a user with enriched data"""
        chats = await self.chat_repo.get_user_chats(user_id)
        
        chat_responses = []
        for chat in chats:
            # Get enriched data (user info, bounty title, last message)
            enriched_data = await self.chat_repo.get_chat_enriched_data(chat.id)
            
            # Get unread count
            unread_count = await self.chat_repo.get_unread_count(chat.id, user_id)
            
            chat_responses.append(
                BountyChatResponse(
                    id=chat.id,
                    bounty_id=chat.bounty_id,  # Return actual bounty_id
                    client_id=chat.client_id,
                    artist_id=chat.artist_id,
                    is_active=chat.is_active,
                    created_at=chat.created_at,
                    updated_at=chat.updated_at,
                    last_message_at=chat.last_message_at,
                    unread_count=unread_count,
                    # User information
                    client_username=enriched_data.get('client_username') if enriched_data else None,
                    artist_username=enriched_data.get('artist_username') if enriched_data else None,
                    client_avatar=enriched_data.get('client_avatar') if enriched_data else None,
                    artist_avatar=enriched_data.get('artist_avatar') if enriched_data else None,
                    # Bounty context
                    bounty_title=enriched_data.get('bounty_title') if enriched_data else None,
                    last_message_preview=enriched_data.get('last_message_preview') if enriched_data else None
                )
            )
        
        return ChatListResponse(
            chats=chat_responses,
            total=len(chat_responses)
        )
    
    async def send_text_message(
        self,
        bounty_id: UUID,
        user_id: UUID,
        message_data: MessageCreate
    ) -> MessageResponse:
        """Send a text message"""
        # Get chat
        chat_response = await self.get_or_create_chat(bounty_id, user_id)
        
        # Create message with bounty context
        message = await self.chat_repo.create_message(
            chat_id=chat_response.id,
            sender_id=user_id,
            bounty_id=message_data.bounty_id or bounty_id,  # Use provided bounty_id or default to current bounty
            message_type=message_data.message_type,
            content=message_data.content,
            reply_to_id=message_data.reply_to_id
        )
        
        return await self._enrich_message_response(message)
    
    def _validate_image_file(self, file: UploadFile) -> None:
        """Validate image file"""
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif']
        max_size = 10 * 1024 * 1024  # 10MB
        
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid image type. Allowed: {', '.join(allowed_types)}"
            )
        
        if file.size and file.size > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image too large. Max size: {max_size / 1024 / 1024}MB"
            )
    
    def _validate_voice_file(self, file: UploadFile) -> None:
        """Validate voice note file"""
        allowed_types = ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg', 'audio/webm', 'audio/m4a']
        max_size = 25 * 1024 * 1024  # 25MB
        
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid audio type. Allowed: {', '.join(allowed_types)}"
            )
        
        if file.size and file.size > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Audio file too large. Max size: {max_size / 1024 / 1024}MB"
            )
    
    async def _upload_file(self, file: UploadFile, folder: str) -> tuple[str, str, int]:
        """Upload file to storage"""
        # Generate secure filename
        extension = get_file_extension(file.filename)
        secure_name = generate_secure_filename(file.filename)
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Upload to OpenDrive
        file_url = await opendrive_storage.upload_file(
            file_content=file_content,
            file_name=secure_name,
            content_type=file.content_type,
            folder=folder
        )
        
        if not file_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file"
            )
        
        return file_url, secure_name, file_size
    
    async def send_image_message(
        self,
        bounty_id: UUID,
        user_id: UUID,
        image_file: UploadFile,
        caption: Optional[str] = None,
        reply_to_id: Optional[UUID] = None,
        message_bounty_id: Optional[UUID] = None
    ) -> MessageResponse:
        """Send an image message"""
        # Validate image
        self._validate_image_file(image_file)
        
        # Get chat
        chat_response = await self.get_or_create_chat(bounty_id, user_id)
        
        # Upload image
        file_url, secure_name, file_size = await self._upload_file(image_file, "chat_images")
        
        # Create message with bounty context
        message = await self.chat_repo.create_message(
            chat_id=chat_response.id,
            sender_id=user_id,
            bounty_id=message_bounty_id or bounty_id,
            message_type="image",
            content=caption,
            file_url=file_url,
            file_name=secure_name,
            file_size=file_size,
            file_type=image_file.content_type,
            thumbnail_url=file_url,  # Use same URL for now
            reply_to_id=reply_to_id
        )
        
        return await self._enrich_message_response(message)
    
    async def send_voice_message(
        self,
        bounty_id: UUID,
        user_id: UUID,
        voice_file: UploadFile,
        duration: Optional[int] = None,
        reply_to_id: Optional[UUID] = None,
        message_bounty_id: Optional[UUID] = None
    ) -> MessageResponse:
        """Send a voice note message"""
        # Validate voice file
        self._validate_voice_file(voice_file)
        
        # Get chat
        chat_response = await self.get_or_create_chat(bounty_id, user_id)
        
        # Upload voice file
        file_url, secure_name, file_size = await self._upload_file(voice_file, "chat_voice")
        
        # Create message with bounty context
        message = await self.chat_repo.create_message(
            chat_id=chat_response.id,
            sender_id=user_id,
            bounty_id=message_bounty_id or bounty_id,
            message_type="voice",
            file_url=file_url,
            file_name=secure_name,
            file_size=file_size,
            file_type=voice_file.content_type,
            voice_duration=duration,
            reply_to_id=reply_to_id
        )
        
        return await self._enrich_message_response(message)
    
    async def get_messages(
        self,
        bounty_id: UUID,
        user_id: UUID,
        page: int = 1,
        limit: int = 50,
        before_message_id: Optional[UUID] = None,
        filter_by_bounty: bool = False
    ) -> MessageListResponse:
        """Get messages for a bounty chat with optional bounty filtering"""
        # Get chat and verify access
        chat_response = await self.get_or_create_chat(bounty_id, user_id)
        
        # Get messages
        skip = (page - 1) * limit
        messages, total = await self.chat_repo.get_messages(
            chat_id=chat_response.id,
            skip=skip,
            limit=limit,
            before_message_id=before_message_id,
            bounty_id=bounty_id if filter_by_bounty else None
        )
        
        # Enrich messages
        message_responses = []
        for message in messages:
            message_responses.append(await self._enrich_message_response(message))
        
        return MessageListResponse(
            messages=message_responses,
            total=total,
            page=page,
            limit=limit,
            has_more=skip + len(messages) < total
        )
    
    async def update_message(
        self,
        message_id: UUID,
        user_id: UUID,
        message_data: MessageUpdate
    ) -> MessageResponse:
        """Update a message (text only)"""
        # Get message
        message = await self.chat_repo.get_message_by_id(message_id)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )
        
        # Verify sender
        if message.sender_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to edit this message"
            )
        
        # Only text messages can be edited
        if message.message_type != "text":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only text messages can be edited"
            )
        
        # Update message
        updated_message = await self.chat_repo.update_message(message_id, message_data.content)
        
        return await self._enrich_message_response(updated_message)
    
    async def delete_message(self, message_id: UUID, user_id: UUID) -> dict:
        """Delete a message"""
        # Get message
        message = await self.chat_repo.get_message_by_id(message_id)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )
        
        # Verify sender
        if message.sender_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this message"
            )
        
        # Delete message
        success = await self.chat_repo.delete_message(message_id)
        
        if success:
            return {"message": "Message deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete message"
            )
    
    async def mark_as_read(
        self,
        bounty_id: UUID,
        user_id: UUID,
        message_ids: List[UUID]
    ) -> dict:
        """Mark messages as read"""
        # Verify access to chat
        await self.get_or_create_chat(bounty_id, user_id)
        
        # Mark messages as read
        count = await self.chat_repo.mark_messages_as_read(message_ids, user_id)
        
        return {"marked_as_read": count}
    
    async def get_unread_count(self, bounty_id: UUID, user_id: UUID) -> UnreadCountResponse:
        """Get unread message count"""
        # Get chat
        chat_response = await self.get_or_create_chat(bounty_id, user_id)
        
        # Get unread count
        unread_count = await self.chat_repo.get_unread_count(chat_response.id, user_id)
        
        return UnreadCountResponse(
            chat_id=chat_response.id,
            unread_count=unread_count
        )
