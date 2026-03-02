"""
Unified Messages API - Aggregates messages from all sources
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_current_user, get_db
from app.models.user import User

router = APIRouter()


@router.get("/inbox")
async def get_inbox(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    type: Optional[str] = Query("all", regex="^(all|bounty_chat|support|system)$"),
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get unified inbox with messages from all sources
    
    Sources:
    - bounty_chat: Messages from bounty conversations
    - support: Support ticket messages (placeholder)
    - system: System notifications
    """
    from sqlalchemy import select, func, and_, or_
    from app.models.bounty_chat import BountyChatMessage, BountyChat
    from app.models.notification import Notification
    from app.models.user import User as UserModel
    from app.models.bounty import Bounty
    from datetime import datetime
    
    messages = []
    
    # 1. Get Bounty Chat Messages
    if type in ["all", "bounty_chat"]:
        # Get chats where user is participant
        chats_query = select(BountyChat).where(
            or_(
                BountyChat.client_id == current_user.id,
                BountyChat.artist_id == current_user.id
            )
        )
        chats_result = await db.execute(chats_query)
        user_chats = chats_result.scalars().all()
        chat_ids = [chat.id for chat in user_chats]
        
        if chat_ids:
            # Get messages from these chats
            chat_messages_query = select(BountyChatMessage).where(
                and_(
                    BountyChatMessage.chat_id.in_(chat_ids),
                    BountyChatMessage.is_deleted == False
                )
            )
            
            if unread_only:
                chat_messages_query = chat_messages_query.where(
                    and_(
                        BountyChatMessage.is_read == False,
                        BountyChatMessage.sender_id != current_user.id
                    )
                )
            
            chat_messages_result = await db.execute(chat_messages_query)
            chat_messages = chat_messages_result.scalars().all()
            
            # Enrich with user and bounty info
            for msg in chat_messages:
                # Get sender info
                sender_result = await db.execute(
                    select(UserModel.username, UserModel.avatar_url).where(UserModel.id == msg.sender_id)
                )
                sender = sender_result.first()
                
                # Get bounty info
                bounty_title = None
                if msg.bounty_id:
                    bounty_result = await db.execute(
                        select(Bounty.title).where(Bounty.id == msg.bounty_id)
                    )
                    bounty_title = bounty_result.scalar_one_or_none()
                
                # Format content preview
                preview = ""
                if msg.message_type == "text" and msg.content:
                    preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                elif msg.message_type == "image":
                    preview = "📷 Image" + (f": {msg.content[:50]}" if msg.content else "")
                elif msg.message_type == "voice":
                    preview = f"🎤 Voice message ({msg.voice_duration}s)" if msg.voice_duration else "🎤 Voice message"
                elif msg.message_type == "link":
                    preview = f"🔗 {msg.content[:80]}" if msg.content else "🔗 Link"
                
                messages.append({
                    "id": f"bounty_chat_{msg.id}",
                    "type": "bounty_chat",
                    "from_user_id": str(msg.sender_id),
                    "from_username": sender[0] if sender else "Unknown",
                    "from_avatar": sender[1] if sender else None,
                    "subject": f"Bounty: {bounty_title}" if bounty_title else "Bounty Chat",
                    "preview": preview,
                    "content": msg.content or "",
                    "related_id": str(msg.bounty_id) if msg.bounty_id else None,
                    "related_title": bounty_title,
                    "is_read": msg.is_read if msg.sender_id != current_user.id else True,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                    "updated_at": msg.updated_at.isoformat() if msg.updated_at else None
                })
    
    # 2. Get System Notifications
    if type in ["all", "system"]:
        notifications_query = select(Notification).where(
            Notification.user_id == current_user.id
        )
        
        if unread_only:
            notifications_query = notifications_query.where(Notification.is_read == False)
        
        notifications_result = await db.execute(notifications_query)
        notifications = notifications_result.scalars().all()
        
        for notif in notifications:
            messages.append({
                "id": f"system_{notif.id}",
                "type": "system",
                "from_user_id": None,
                "from_username": "SDModels",
                "from_avatar": None,
                "subject": notif.title or "Notification",
                "preview": (notif.message[:100] + "...") if notif.message and len(notif.message) > 100 else (notif.message or ""),
                "content": notif.message or "",
                "related_id": str(notif.related_id) if notif.related_id else None,
                "related_title": notif.related_title,
                "is_read": notif.is_read,
                "created_at": notif.created_at.isoformat() if notif.created_at else None,
                "updated_at": notif.created_at.isoformat() if notif.created_at else None
            })
    
    # 3. Support Tickets (placeholder - not implemented yet)
    if type in ["all", "support"]:
        # TODO: Implement support ticket integration
        pass
    
    # Sort by created_at descending (newest first)
    messages.sort(key=lambda x: x["created_at"] or "", reverse=True)
    
    # Calculate unread count
    unread_count = sum(1 for msg in messages if not msg["is_read"])
    
    # Paginate
    total = len(messages)
    start = (page - 1) * limit
    end = start + limit
    paginated_messages = messages[start:end]
    
    return {
        "data": paginated_messages,
        "total": total,
        "unread_count": unread_count,
        "page": page,
        "limit": limit
    }


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get total unread message count across all types"""
    from sqlalchemy import select, func, and_, or_
    from app.models.bounty_chat import BountyChatMessage, BountyChat
    from app.models.notification import Notification
    
    # Count unread bounty chat messages
    chats_query = select(BountyChat.id).where(
        or_(
            BountyChat.client_id == current_user.id,
            BountyChat.artist_id == current_user.id
        )
    )
    chats_result = await db.execute(chats_query)
    chat_ids = [row[0] for row in chats_result.fetchall()]
    
    bounty_chat_unread = 0
    if chat_ids:
        bounty_chat_query = select(func.count()).select_from(BountyChatMessage).where(
            and_(
                BountyChatMessage.chat_id.in_(chat_ids),
                BountyChatMessage.sender_id != current_user.id,
                BountyChatMessage.is_read == False,
                BountyChatMessage.is_deleted == False
            )
        )
        bounty_chat_result = await db.execute(bounty_chat_query)
        bounty_chat_unread = bounty_chat_result.scalar_one()
    
    # Count unread notifications
    notifications_query = select(func.count()).select_from(Notification).where(
        and_(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        )
    )
    notifications_result = await db.execute(notifications_query)
    system_unread = notifications_result.scalar_one()
    
    # Support tickets (placeholder)
    support_unread = 0
    
    total = bounty_chat_unread + system_unread + support_unread
    
    return {
        "data": {
            "total": total,
            "by_type": {
                "bounty_chat": bounty_chat_unread,
                "support": support_unread,
                "system": system_unread,
                "review": 0,  # Not implemented
                "request": 0  # Not implemented
            }
        }
    }


@router.post("/{message_id}/mark-read")
async def mark_message_as_read(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark a specific message as read"""
    from sqlalchemy import select, update
    from app.models.bounty_chat import BountyChatMessage
    from app.models.notification import Notification
    from datetime import datetime
    
    # Parse message ID to determine type
    if message_id.startswith("bounty_chat_"):
        # Bounty chat message
        msg_uuid = message_id.replace("bounty_chat_", "")
        
        result = await db.execute(
            update(BountyChatMessage)
            .where(BountyChatMessage.id == UUID(msg_uuid))
            .values(is_read=True, read_at=datetime.utcnow())
        )
        await db.commit()
        
        return {
            "data": {
                "id": message_id,
                "is_read": True,
                "read_at": datetime.utcnow().isoformat()
            }
        }
    
    elif message_id.startswith("system_"):
        # System notification
        notif_uuid = message_id.replace("system_", "")
        
        result = await db.execute(
            update(Notification)
            .where(Notification.id == UUID(notif_uuid))
            .values(is_read=True)
        )
        await db.commit()
        
        return {
            "data": {
                "id": message_id,
                "is_read": True,
                "read_at": datetime.utcnow().isoformat()
            }
        }
    
    else:
        return {
            "data": {
                "id": message_id,
                "is_read": False,
                "error": "Unknown message type"
            }
        }


@router.post("/mark-all-read")
async def mark_all_messages_as_read(
    type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark all messages as read"""
    from sqlalchemy import select, update, and_, or_
    from app.models.bounty_chat import BountyChatMessage, BountyChat
    from app.models.notification import Notification
    from datetime import datetime
    
    marked_count = 0
    
    # Mark bounty chat messages as read
    if not type or type in ["all", "bounty_chat"]:
        # Get user's chats
        chats_query = select(BountyChat.id).where(
            or_(
                BountyChat.client_id == current_user.id,
                BountyChat.artist_id == current_user.id
            )
        )
        chats_result = await db.execute(chats_query)
        chat_ids = [row[0] for row in chats_result.fetchall()]
        
        if chat_ids:
            result = await db.execute(
                update(BountyChatMessage)
                .where(
                    and_(
                        BountyChatMessage.chat_id.in_(chat_ids),
                        BountyChatMessage.sender_id != current_user.id,
                        BountyChatMessage.is_read == False
                    )
                )
                .values(is_read=True, read_at=datetime.utcnow())
            )
            marked_count += result.rowcount
    
    # Mark notifications as read
    if not type or type in ["all", "system"]:
        result = await db.execute(
            update(Notification)
            .where(
                and_(
                    Notification.user_id == current_user.id,
                    Notification.is_read == False
                )
            )
            .values(is_read=True)
        )
        marked_count += result.rowcount
    
    await db.commit()
    
    return {
        "data": {
            "marked_count": marked_count,
            "type": type or "all"
        }
    }


@router.post("/{message_id}/reply")
async def reply_to_message(
    message_id: str,
    content: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reply to a message"""
    from sqlalchemy import select
    from app.models.bounty_chat import BountyChatMessage
    from datetime import datetime
    
    # Only bounty chat messages support replies for now
    if message_id.startswith("bounty_chat_"):
        msg_uuid = message_id.replace("bounty_chat_", "")
        
        # Get original message
        original_msg_result = await db.execute(
            select(BountyChatMessage).where(BountyChatMessage.id == UUID(msg_uuid))
        )
        original_msg = original_msg_result.scalar_one_or_none()
        
        if not original_msg:
            return {"error": "Message not found"}
        
        # Create reply message
        reply_msg = BountyChatMessage(
            chat_id=original_msg.chat_id,
            sender_id=current_user.id,
            bounty_id=original_msg.bounty_id,
            message_type="text",
            content=content,
            reply_to_id=original_msg.id
        )
        
        db.add(reply_msg)
        await db.commit()
        await db.refresh(reply_msg)
        
        return {
            "data": {
                "id": str(reply_msg.id),
                "message_id": message_id,
                "content": content,
                "created_at": reply_msg.created_at.isoformat()
            }
        }
    
    else:
        return {"error": "Reply not supported for this message type"}
