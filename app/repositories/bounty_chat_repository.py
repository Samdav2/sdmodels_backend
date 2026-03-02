from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.orm import selectinload
from app.models.bounty_chat import BountyChat, BountyChatMessage, BountyChatAttachment
from app.models.user import User


class BountyChatRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_or_create_chat(self, client_id: UUID, artist_id: UUID) -> BountyChat:
        """Get existing chat or create new one for user pair"""
        # Ensure consistent ordering (smaller UUID first)
        user1_id = min(client_id, artist_id)
        user2_id = max(client_id, artist_id)
        
        # Check if chat exists for this user pair
        result = await self.db.execute(
            select(BountyChat).where(
                or_(
                    and_(BountyChat.client_id == user1_id, BountyChat.artist_id == user2_id),
                    and_(BountyChat.client_id == user2_id, BountyChat.artist_id == user1_id)
                )
            )
        )
        chat = result.scalar_one_or_none()
        
        if not chat:
            # Create new chat
            chat = BountyChat(
                client_id=client_id,
                artist_id=artist_id
            )
            self.db.add(chat)
            await self.db.commit()
            await self.db.refresh(chat)
        
        return chat
    
    async def get_chat_by_id(self, chat_id: UUID) -> Optional[BountyChat]:
        """Get chat by ID"""
        result = await self.db.execute(
            select(BountyChat).where(BountyChat.id == chat_id)
        )
        return result.scalar_one_or_none()
    
    async def get_chat_by_bounty(self, bounty_id: UUID) -> Optional[BountyChat]:
        """Get chat by bounty ID (deprecated, for backward compatibility)"""
        result = await self.db.execute(
            select(BountyChat).where(BountyChat.bounty_id == bounty_id)
        )
        return result.scalar_one_or_none()
    
    async def get_chat_by_user_pair(self, user1_id: UUID, user2_id: UUID) -> Optional[BountyChat]:
        """Get chat by user pair"""
        result = await self.db.execute(
            select(BountyChat).where(
                or_(
                    and_(BountyChat.client_id == user1_id, BountyChat.artist_id == user2_id),
                    and_(BountyChat.client_id == user2_id, BountyChat.artist_id == user1_id)
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_user_chats(self, user_id: UUID) -> List[BountyChat]:
        """Get all chats for a user (as client or artist)"""
        result = await self.db.execute(
            select(BountyChat).where(
                or_(
                    BountyChat.client_id == user_id,
                    BountyChat.artist_id == user_id
                )
            ).where(BountyChat.is_active == True)
            .order_by(BountyChat.last_message_at.desc().nullslast())
        )
        return list(result.scalars().all())
    
    async def get_chat_enriched_data(self, chat_id: UUID) -> Optional[dict]:
        """Get enriched chat data with user info, bounty title, and last message"""
        from app.models.bounty import Bounty
        
        # Get chat
        chat_result = await self.db.execute(
            select(BountyChat).where(BountyChat.id == chat_id)
        )
        chat = chat_result.scalar_one_or_none()
        if not chat:
            return None
        
        # Get client info
        client_result = await self.db.execute(
            select(User.username, User.avatar_url)
            .where(User.id == chat.client_id)
        )
        client = client_result.first()
        
        # Get artist info
        artist_result = await self.db.execute(
            select(User.username, User.avatar_url)
            .where(User.id == chat.artist_id)
        )
        artist = artist_result.first()
        
        # Get last message preview
        last_message_result = await self.db.execute(
            select(BountyChatMessage.content, BountyChatMessage.message_type)
            .where(
                and_(
                    BountyChatMessage.chat_id == chat_id,
                    BountyChatMessage.is_deleted == False
                )
            )
            .order_by(BountyChatMessage.created_at.desc())
            .limit(1)
        )
        last_message = last_message_result.first()
        
        # Get bounty title from the most recent bounty in messages
        bounty_title = None
        bounty_result = await self.db.execute(
            select(Bounty.title)
            .join(BountyChatMessage, BountyChatMessage.bounty_id == Bounty.id)
            .where(
                and_(
                    BountyChatMessage.chat_id == chat_id,
                    BountyChatMessage.bounty_id.isnot(None)
                )
            )
            .order_by(BountyChatMessage.created_at.desc())
            .limit(1)
        )
        bounty = bounty_result.first()
        if bounty:
            bounty_title = bounty[0]
        
        # Format last message preview
        last_message_preview = None
        if last_message:
            content, msg_type = last_message
            if msg_type == "text" and content:
                last_message_preview = content[:50] + "..." if len(content) > 50 else content
            elif msg_type == "image":
                last_message_preview = "📷 Image"
            elif msg_type == "voice":
                last_message_preview = "🎤 Voice message"
            elif msg_type == "link":
                last_message_preview = "🔗 Link"
        
        return {
            "client_username": client[0] if client else None,
            "client_avatar": client[1] if client else None,
            "artist_username": artist[0] if artist else None,
            "artist_avatar": artist[1] if artist else None,
            "bounty_title": bounty_title,
            "last_message_preview": last_message_preview
        }
    
    async def create_message(
        self,
        chat_id: UUID,
        sender_id: UUID,
        message_type: str,
        bounty_id: Optional[UUID] = None,
        content: Optional[str] = None,
        file_url: Optional[str] = None,
        file_name: Optional[str] = None,
        file_size: Optional[int] = None,
        file_type: Optional[str] = None,
        voice_duration: Optional[int] = None,
        thumbnail_url: Optional[str] = None,
        reply_to_id: Optional[UUID] = None
    ) -> BountyChatMessage:
        """Create a new message"""
        message = BountyChatMessage(
            chat_id=chat_id,
            sender_id=sender_id,
            bounty_id=bounty_id,
            message_type=message_type,
            content=content,
            file_url=file_url,
            file_name=file_name,
            file_size=file_size,
            file_type=file_type,
            voice_duration=voice_duration,
            thumbnail_url=thumbnail_url,
            reply_to_id=reply_to_id
        )
        self.db.add(message)
        
        # Update chat's last_message_at
        await self.db.execute(
            update(BountyChat)
            .where(BountyChat.id == chat_id)
            .values(last_message_at=datetime.utcnow(), updated_at=datetime.utcnow())
        )
        
        await self.db.commit()
        await self.db.refresh(message)
        return message
    
    async def add_attachments(self, message_id: UUID, attachments: List[dict]) -> List[BountyChatAttachment]:
        """Add multiple attachments to a message"""
        attachment_objects = []
        for idx, attachment_data in enumerate(attachments):
            attachment = BountyChatAttachment(
                message_id=message_id,
                file_url=attachment_data['file_url'],
                file_name=attachment_data['file_name'],
                file_size=attachment_data['file_size'],
                file_type=attachment_data['file_type'],
                thumbnail_url=attachment_data.get('thumbnail_url'),
                width=attachment_data.get('width'),
                height=attachment_data.get('height'),
                order=idx
            )
            self.db.add(attachment)
            attachment_objects.append(attachment)
        
        await self.db.commit()
        for attachment in attachment_objects:
            await self.db.refresh(attachment)
        
        return attachment_objects
    
    async def get_messages(
        self,
        chat_id: UUID,
        skip: int = 0,
        limit: int = 50,
        before_message_id: Optional[UUID] = None,
        bounty_id: Optional[UUID] = None
    ) -> Tuple[List[BountyChatMessage], int]:
        """Get messages for a chat with pagination and optional bounty filter"""
        # Include deleted messages - they will be shown with placeholder text
        query = select(BountyChatMessage).where(
            BountyChatMessage.chat_id == chat_id
        )
        
        # Filter by bounty if specified
        if bounty_id:
            query = query.where(BountyChatMessage.bounty_id == bounty_id)
        
        # If before_message_id is provided, get messages before that message
        if before_message_id:
            before_message = await self.get_message_by_id(before_message_id)
            if before_message:
                query = query.where(BountyChatMessage.created_at < before_message.created_at)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Get messages
        query = query.order_by(BountyChatMessage.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        messages = list(result.scalars().all())
        
        # Reverse to show oldest first
        messages.reverse()
        
        return messages, total
    
    async def get_message_by_id(self, message_id: UUID) -> Optional[BountyChatMessage]:
        """Get message by ID"""
        result = await self.db.execute(
            select(BountyChatMessage).where(BountyChatMessage.id == message_id)
        )
        return result.scalar_one_or_none()
    
    async def get_message_attachments(self, message_id: UUID) -> List[BountyChatAttachment]:
        """Get all attachments for a message"""
        result = await self.db.execute(
            select(BountyChatAttachment)
            .where(BountyChatAttachment.message_id == message_id)
            .order_by(BountyChatAttachment.order)
        )
        return list(result.scalars().all())
    
    async def update_message(self, message_id: UUID, content: str) -> Optional[BountyChatMessage]:
        """Update message content"""
        message = await self.get_message_by_id(message_id)
        if message:
            message.content = content
            message.is_edited = True
            message.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(message)
        return message
    
    async def delete_message(self, message_id: UUID) -> bool:
        """Soft delete a message"""
        message = await self.get_message_by_id(message_id)
        if message:
            message.is_deleted = True
            message.updated_at = datetime.utcnow()
            await self.db.commit()
            return True
        return False
    
    async def mark_messages_as_read(self, message_ids: List[UUID], user_id: UUID) -> int:
        """Mark multiple messages as read"""
        result = await self.db.execute(
            update(BountyChatMessage)
            .where(
                and_(
                    BountyChatMessage.id.in_(message_ids),
                    BountyChatMessage.sender_id != user_id,  # Don't mark own messages
                    BountyChatMessage.is_read == False
                )
            )
            .values(is_read=True, read_at=datetime.utcnow())
        )
        await self.db.commit()
        return result.rowcount
    
    async def get_unread_count(self, chat_id: UUID, user_id: UUID) -> int:
        """Get unread message count for a user in a chat"""
        result = await self.db.execute(
            select(func.count())
            .select_from(BountyChatMessage)
            .where(
                and_(
                    BountyChatMessage.chat_id == chat_id,
                    BountyChatMessage.sender_id != user_id,
                    BountyChatMessage.is_read == False,
                    BountyChatMessage.is_deleted == False
                )
            )
        )
        return result.scalar()
    
    async def get_user_info(self, user_id: UUID) -> Optional[dict]:
        """Get user info for message enrichment"""
        result = await self.db.execute(
            select(User.username, User.avatar_url)
            .where(User.id == user_id)
        )
        user = result.first()
        if user:
            return {
                "username": user[0],
                "avatar": user[1]
            }
        return None
    
    async def get_bounty_info(self, bounty_id: UUID) -> Optional[dict]:
        """Get bounty info for message context"""
        from app.models.bounty import Bounty
        result = await self.db.execute(
            select(Bounty.title, Bounty.status)
            .where(Bounty.id == bounty_id)
        )
        bounty = result.first()
        if bounty:
            return {
                "title": bounty[0],
                "status": bounty[1]
            }
        return None
