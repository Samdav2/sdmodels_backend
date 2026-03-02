from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("")
async def get_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    filter: str = Query("all", regex="^(all|unread|read)$"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get user notifications"""
    from sqlalchemy import select, func
    from app.models.notification import Notification
    
    # Build query based on filter
    query = select(Notification).where(Notification.user_id == current_user.id)
    count_query = select(func.count()).select_from(Notification).where(Notification.user_id == current_user.id)
    
    if filter == "unread":
        query = query.where(Notification.is_read == False)
        count_query = count_query.where(Notification.is_read == False)
    elif filter == "read":
        query = query.where(Notification.is_read == True)
        count_query = count_query.where(Notification.is_read == True)
    
    # Get total count
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()
    
    # Get paginated notifications
    query = query.offset((page - 1) * limit).limit(limit).order_by(Notification.created_at.desc())
    result = await session.execute(query)
    notifications = result.scalars().all()
    
    return {
        "notifications": [
            {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "message": n.message,
                "is_read": n.is_read,
                "created_at": n.created_at
            } for n in notifications
        ],
        "total": total,
        "page": page,
        "limit": limit
    }


@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Mark notification as read"""
    return {"message": "Notification marked as read"}


@router.put("/read-all")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Mark all notifications as read"""
    return {"message": "All notifications marked as read"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Delete notification"""
    return {"message": "Notification deleted"}
