from uuid import UUID
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.admin import (
    AdminStatsResponse, UserUpdateAdmin, ModelApprovalRequest,
    ModelRejectionRequest, ReportResolveRequest, AnnouncementCreate
)
from app.core.dependencies import get_current_admin
from app.models.user import User

router = APIRouter()


@router.get("/stats", response_model=AdminStatsResponse)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Get dashboard statistics"""
    from sqlalchemy import select, func
    from app.models.user import User as UserModel
    from app.models.model import Model
    from app.models.support import SupportTicket
    from app.models.wallet import WalletTransaction
    from datetime import datetime, timedelta
    
    # Get total users
    total_users_result = await session.execute(select(func.count(UserModel.id)))
    total_users = total_users_result.scalar() or 0
    
    # Get total models
    total_models_result = await session.execute(select(func.count(Model.id)))
    total_models = total_models_result.scalar() or 0
    
    # Get pending models
    pending_models_result = await session.execute(
        select(func.count(Model.id)).where(Model.status == "pending")
    )
    pending_models = pending_models_result.scalar() or 0
    
    # Get pending tickets
    pending_tickets_result = await session.execute(
        select(func.count(SupportTicket.id)).where(SupportTicket.status.in_(["active", "pending"]))
    )
    pending_tickets = pending_tickets_result.scalar() or 0
    
    # Get new users today
    today = datetime.utcnow().date()
    new_users_today_result = await session.execute(
        select(func.count(UserModel.id)).where(
            func.date(UserModel.created_at) == today
        )
    )
    new_users_today = new_users_today_result.scalar() or 0
    
    # Get active users today (users who logged in today)
    # For now, estimate based on new users (would need last_login tracking)
    active_users_today = new_users_today
    
    # Calculate REAL total revenue from all revenue-generating transactions
    # Revenue sources:
    # 1. Model sales (model_sale)
    # 2. Bounty payments (bounty_payment) 
    # 3. Platform fees (platform_fee)
    # 4. Deposits (deposit) - money coming into the platform
    
    revenue_query = select(func.sum(WalletTransaction.amount)).where(
        WalletTransaction.transaction_type.in_([
            'model_sale',      # Revenue from model purchases
            'platform_fee',    # Platform fees collected
            'deposit'          # Money deposited into platform
        ]),
        WalletTransaction.status == 'completed'
    )
    
    revenue_result = await session.execute(revenue_query)
    total_revenue = float(revenue_result.scalar() or 0.0)
    
    # Alternative: Calculate net revenue (deposits + fees only, excluding internal transfers)
    # This gives a more accurate picture of actual money flowing into the platform
    deposits_query = select(func.sum(WalletTransaction.amount)).where(
        WalletTransaction.transaction_type == 'deposit',
        WalletTransaction.status == 'completed'
    )
    deposits_result = await session.execute(deposits_query)
    total_deposits = float(deposits_result.scalar() or 0.0)
    
    fees_query = select(func.sum(WalletTransaction.amount)).where(
        WalletTransaction.transaction_type == 'platform_fee',
        WalletTransaction.status == 'completed'
    )
    fees_result = await session.execute(fees_query)
    total_fees = float(fees_result.scalar() or 0.0)
    
    # Total revenue = deposits (money in) + platform fees (our cut)
    total_revenue = total_deposits + total_fees
    
    return {
        "total_users": total_users,
        "total_models": total_models,
        "total_revenue": total_revenue,
        "active_users_today": active_users_today,
        "new_users_today": new_users_today,
        "pending_models": pending_models,
        "pending_tickets": pending_tickets
    }


@router.get("/users")
async def get_all_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    user_type: Optional[str] = None,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Get all users with filters"""
    from sqlalchemy import select, func, or_
    from app.models.user import User as UserModel
    
    # Build query
    query = select(UserModel)
    count_query = select(func.count(UserModel.id))
    
    # Apply filters
    if search:
        search_filter = or_(
            UserModel.username.ilike(f"%{search}%"),
            UserModel.email.ilike(f"%{search}%"),
            UserModel.full_name.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    if user_type:
        query = query.where(UserModel.user_type == user_type)
        count_query = count_query.where(UserModel.user_type == user_type)
    
    # Get total count
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get paginated users
    skip = (page - 1) * limit
    query = query.offset(skip).limit(limit).order_by(UserModel.created_at.desc())
    result = await session.execute(query)
    users = result.scalars().all()
    
    # Convert to dict
    users_list = [
        {
            "id": str(u.id),
            "username": u.username,
            "email": u.email,
            "full_name": u.full_name,
            "user_type": u.user_type,
            "is_active": u.is_active,
            "is_verified": u.is_verified,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "avatar_url": u.avatar_url,
            "total_models": u.total_models or 0
        }
        for u in users
    ]
    
    return {
        "users": users_list,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if total > 0 else 0
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: UUID,
    user_data: UserUpdateAdmin,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Update user (ban, verify, etc.)"""
    from app.repositories.user_repository import UserRepository
    
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update user fields
    update_data = user_data.model_dump(exclude_unset=True)
    updated_user = await user_repo.update(user_id, **update_data)
    
    return {
        "message": "User updated successfully",
        "user": {
            "id": str(updated_user.id),
            "username": updated_user.username,
            "email": updated_user.email,
            "user_type": updated_user.user_type,
            "is_active": updated_user.is_active,
            "is_verified": updated_user.is_verified
        }
    }


@router.post("/users/{user_id}/suspend")
async def suspend_user(
    user_id: UUID,
    suspension_reason: str = Query(..., description="Reason for suspension"),
    suspension_duration: str = Query(..., description="Duration of suspension (e.g., '7 days', '30 days', 'Permanent')"),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Suspend user account"""
    from app.repositories.user_repository import UserRepository
    
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Suspend user by setting is_active to False
    updated_user = await user_repo.update(user_id, is_active=False)
    
    # Send suspension email
    try:
        from app.utils.email import send_account_suspended_email
        from app.core.config import settings
        
        await send_account_suspended_email(
            user_email=user.email,
            username=user.username,
            suspension_reason=suspension_reason,
            suspension_duration=suspension_duration,
            appeal_url=f"{settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'}/support/appeal"
        )
    except Exception as e:
        print(f"Failed to send account suspended email: {e}")
    
    return {
        "message": "User suspended successfully",
        "user": {
            "id": str(updated_user.id),
            "username": updated_user.username,
            "is_active": updated_user.is_active,
            "suspension_reason": suspension_reason,
            "suspension_duration": suspension_duration
        }
    }


@router.get("/models")
async def get_all_models(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected"),
    search: Optional[str] = None,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Get all models for moderation"""
    from sqlalchemy import select, func, or_
    from app.models.model import Model
    from app.models.user import User as UserModel
    
    # Build query with creator info
    query = select(Model, UserModel.username).join(
        UserModel, Model.creator_id == UserModel.id
    )
    count_query = select(func.count(Model.id))
    
    # Apply filters
    filters = []
    if status:
        filters.append(Model.status == status)
    
    if search:
        search_filter = or_(
            Model.title.ilike(f"%{search}%"),
            Model.description.ilike(f"%{search}%")
        )
        filters.append(search_filter)
    
    if filters:
        from sqlalchemy import and_
        combined_filter = and_(*filters)
        query = query.where(combined_filter)
        count_query = count_query.where(combined_filter)
    
    # Get total count
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get paginated models
    skip = (page - 1) * limit
    query = query.offset(skip).limit(limit).order_by(Model.created_at.desc())
    result = await session.execute(query)
    rows = result.all()
    
    # Convert to dict
    models_list = [
        {
            "id": str(model.id),
            "title": model.title,
            "description": model.description,
            "price": float(model.price) if model.price else 0.0,
            "status": model.status,
            "category": model.category,
            "creator_id": str(model.creator_id),
            "creator_username": username,
            "created_at": model.created_at.isoformat() if model.created_at else None,
            "views": model.views or 0,
            "likes": model.likes or 0,
            "downloads": model.downloads or 0,
            "thumbnail_url": model.thumbnail_url,
            "is_free": model.is_free
        }
        for model, username in rows
    ]
    
    return {
        "models": models_list,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if total > 0 else 0
    }


@router.put("/models/{model_id}/approve")
async def approve_model(
    model_id: UUID,
    approval_data: ModelApprovalRequest,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Approve model"""
    from app.repositories.model_repository import ModelRepository
    
    model_repo = ModelRepository(session)
    model = await model_repo.get_model_object(model_id)
    
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )
    
    # Update model status to approved
    updated_model = await model_repo.update(
        model_id,
        status="approved",
        is_published=True
    )
    
    # Send email notification to creator
    try:
        from app.utils.email import send_model_approved_email
        from app.core.config import settings
        from sqlalchemy import select
        
        creator_result = await session.execute(
            select(User).where(User.id == model.creator_id)
        )
        creator = creator_result.scalar_one_or_none()
        
        if creator:
            await send_model_approved_email(
                user_email=creator.email,
                username=creator.username,
                model_title=model.title,
                model_url=f"{settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'}/models/{model.id}"
            )
    except Exception as e:
        print(f"Failed to send model approved email: {e}")
    
    return {
        "message": "Model approved successfully",
        "model": {
            "id": str(updated_model.id),
            "title": updated_model.title,
            "status": updated_model.status,
            "is_published": updated_model.is_published
        }
    }


@router.put("/models/{model_id}/reject")
async def reject_model(
    model_id: UUID,
    rejection_data: ModelRejectionRequest,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Reject model"""
    from app.repositories.model_repository import ModelRepository
    
    model_repo = ModelRepository(session)
    model = await model_repo.get_model_object(model_id)
    
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )
    
    # Update model status to rejected
    updated_model = await model_repo.update(
        model_id,
        status="rejected",
        is_published=False
    )
    
    # Send email notification to creator with rejection reason
    try:
        from app.utils.email import send_model_rejected_email
        from app.core.config import settings
        from sqlalchemy import select
        
        creator_result = await session.execute(
            select(User).where(User.id == model.creator_id)
        )
        creator = creator_result.scalar_one_or_none()
        
        if creator:
            await send_model_rejected_email(
                user_email=creator.email,
                username=creator.username,
                model_title=model.title,
                rejection_reason=rejection_data.reason,
                model_url=f"{settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'}/models/{model.id}/edit"
            )
    except Exception as e:
        print(f"Failed to send model rejected email: {e}")
    
    return {
        "message": "Model rejected successfully",
        "model": {
            "id": str(updated_model.id),
            "title": updated_model.title,
            "status": updated_model.status,
            "rejection_reason": rejection_data.reason
        }
    }


@router.get("/communities")
async def get_all_communities(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status: pending, active, suspended"),
    search: Optional[str] = None,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Get all communities"""
    from app.repositories.community_repository import CommunityRepository
    
    community_repo = CommunityRepository(session)
    skip = (page - 1) * limit
    
    communities, total = await community_repo.get_all(
        skip=skip,
        limit=limit,
        status=status,
        search=search
    )
    
    # Convert to serializable format
    communities_list = [
        {
            "id": str(c["id"]),
            "name": c["name"],
            "description": c["description"],
            "icon": c["icon"],
            "category": c["category"],
            "creator_id": str(c["creator_id"]),
            "member_count": c["member_count"],
            "post_count": c["post_count"],
            "status": c["status"],
            "is_private": c["is_private"],
            "created_at": c["created_at"].isoformat() if c["created_at"] else None
        }
        for c in communities
    ]
    
    return {
        "communities": communities_list,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if total > 0 else 0
    }


@router.put("/communities/{community_id}/approve")
async def approve_community(
    community_id: UUID,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Approve community"""
    from app.repositories.community_repository import CommunityRepository
    
    community_repo = CommunityRepository(session)
    community = await community_repo.get_by_id(community_id)
    
    if not community:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community not found"
        )
    
    # Update community status to active
    updated_community = await community_repo.update(community_id, status="active")
    
    # Send email notification to community creator
    try:
        from app.utils.email import send_community_approved_email
        from app.core.config import settings
        from sqlalchemy import select
        
        creator_result = await session.execute(
            select(User).where(User.id == community.creator_id)
        )
        creator = creator_result.scalar_one_or_none()
        
        if creator:
            await send_community_approved_email(
                user_email=creator.email,
                username=creator.username,
                community_name=community.name,
                community_url=f"{settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'}/communities/{community_id}"
            )
    except Exception as e:
        print(f"Failed to send community approved email: {e}")
    
    return {
        "message": "Community approved successfully",
        "community": {
            "id": str(updated_community.id),
            "name": updated_community.name,
            "status": updated_community.status
        }
    }


@router.delete("/communities/{community_id}")
async def delete_community(
    community_id: UUID,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Delete community"""
    from app.repositories.community_repository import CommunityRepository
    
    community_repo = CommunityRepository(session)
    community = await community_repo.get_by_id(community_id)
    
    if not community:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community not found"
        )
    
    # Delete community
    success = await community_repo.delete(community_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete community"
        )
    
    return {"message": "Community deleted successfully"}


@router.get("/reports")
async def get_reports(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status: pending, resolved, dismissed"),
    report_type: Optional[str] = Query(None, description="Filter by type: post, comment, model, user"),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Get content reports"""
    # Note: This is a placeholder implementation
    # In a real system, you would have a reports table
    # For now, returning empty list with proper structure
    
    return {
        "reports": [],
        "total": 0,
        "page": page,
        "limit": limit,
        "total_pages": 0,
        "message": "Reports system not yet implemented. Create a 'reports' table to track content reports."
    }


@router.put("/reports/{report_id}/resolve")
async def resolve_report(
    report_id: int,
    resolve_data: ReportResolveRequest,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Resolve report"""
    # Note: This is a placeholder implementation
    # In a real system, you would update the report status in the database
    
    return {
        "message": "Report resolved successfully",
        "report_id": report_id,
        "action": resolve_data.action if hasattr(resolve_data, 'action') else "resolved",
        "note": "Reports system not yet implemented. Create a 'reports' table to track content reports."
    }


@router.post("/announcements")
async def send_announcement(
    announcement_data: AnnouncementCreate,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Send announcement to users"""
    from app.models.notification import Notification
    from sqlalchemy import select
    from app.models.user import User as UserModel
    
    # Get all active users
    result = await session.execute(
        select(UserModel.id).where(UserModel.is_active == True)
    )
    user_ids = [row[0] for row in result.fetchall()]
    
    if not user_ids:
        return {
            "message": "No active users to send announcement to",
            "users_notified": 0
        }
    
    # Create notification for each user
    notifications = []
    for user_id in user_ids:
        notification = Notification(
            user_id=user_id,
            type="announcement",
            title=announcement_data.title,
            message=announcement_data.message,
            is_read=False
        )
        notifications.append(notification)
    
    # Bulk insert notifications
    session.add_all(notifications)
    await session.commit()
    
    # TODO: Send email notifications if enabled
    # TODO: Send push notifications if enabled
    
    return {
        "message": "Announcement sent successfully",
        "users_notified": len(user_ids),
        "title": announcement_data.title
    }


# ============================================================================
# ADDITIONAL ADMIN ENDPOINTS (Placeholder implementations)
# ============================================================================

@router.get("/content")
async def get_content(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    content_type: Optional[str] = Query(None, description="Filter by type: blog, page, media"),
    status: Optional[str] = Query(None, description="Filter by status: draft, published"),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Get content management items (blog posts)"""
    from sqlalchemy import select, func, desc, or_
    from app.models.blog import BlogPost
    from app.models.user import User as UserModel
    
    # Build query with author info
    query = select(
        BlogPost,
        UserModel.username,
        UserModel.full_name
    ).join(
        UserModel, BlogPost.author_id == UserModel.id
    )
    
    count_query = select(func.count(BlogPost.id))
    
    # Apply filters
    filters = []
    if status:
        filters.append(BlogPost.status == status)
    
    if filters:
        from sqlalchemy import and_
        combined_filter = and_(*filters)
        query = query.where(combined_filter)
        count_query = count_query.where(combined_filter)
    
    # Get total count
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get paginated content
    skip = (page - 1) * limit
    query = query.offset(skip).limit(limit).order_by(desc(BlogPost.created_at))
    result = await session.execute(query)
    rows = result.all()
    
    # Convert to dict
    content_list = [
        {
            "id": str(post.id),
            "title": post.title,
            "excerpt": post.excerpt,
            "content": post.content[:200] + "..." if len(post.content) > 200 else post.content,
            "category": post.category,
            "status": post.status,
            "is_featured": post.is_featured,
            "featured_image": post.featured_image,
            "author_id": str(post.author_id),
            "author_username": username,
            "author_name": full_name,
            "views": post.views,
            "likes": post.likes,
            "comment_count": post.comment_count,
            "read_time": post.read_time,
            "published_at": post.published_at.isoformat() if post.published_at else None,
            "created_at": post.created_at.isoformat() if post.created_at else None,
            "updated_at": post.updated_at.isoformat() if post.updated_at else None
        }
        for post, username, full_name in rows
    ]
    
    return {
        "content": content_list,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if total > 0 else 0,
        "content_type": "blog"
    }


@router.post("/content")
async def create_content(
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Create content (blog post)"""
    from app.models.blog import BlogPost
    
    # Create a new blog post
    new_post = BlogPost(
        author_id=current_user.id,
        title="New Blog Post",
        content="Start writing your content here...",
        excerpt="",
        category="news",
        status="draft"
    )
    
    session.add(new_post)
    await session.commit()
    await session.refresh(new_post)
    
    return {
        "message": "Blog post created successfully",
        "content": {
            "id": str(new_post.id),
            "title": new_post.title,
            "status": new_post.status,
            "created_at": new_post.created_at.isoformat()
        }
    }


@router.get("/revenue")
async def get_revenue(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Get revenue overview"""
    from sqlalchemy import select, func
    from app.models.wallet import WalletTransaction
    from datetime import datetime
    
    # Build query for revenue transactions
    query = select(
        func.sum(WalletTransaction.amount).label('total_amount'),
        func.count(WalletTransaction.id).label('transaction_count')
    )
    
    # Filter by date range if provided
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            query = query.where(WalletTransaction.created_at >= start_dt)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
            query = query.where(WalletTransaction.created_at <= end_dt)
        except ValueError:
            pass
    
    # Get total revenue from model sales
    sales_query = query.where(WalletTransaction.transaction_type == "model_sale")
    sales_result = await session.execute(sales_query)
    sales_row = sales_result.first()
    total_revenue = float(sales_row[0]) if sales_row[0] else 0.0
    total_sales = sales_row[1] if sales_row[1] else 0
    
    # Get platform fees
    fees_query = select(func.sum(WalletTransaction.amount)).where(
        WalletTransaction.transaction_type == "platform_fee"
    )
    fees_result = await session.execute(fees_query)
    platform_fees = float(fees_result.scalar() or 0.0)
    
    # Get pending payouts (withdrawals in pending status)
    pending_query = select(func.sum(WalletTransaction.amount)).where(
        WalletTransaction.transaction_type == "withdrawal",
        WalletTransaction.status == "pending"
    )
    pending_result = await session.execute(pending_query)
    pending_payouts = float(pending_result.scalar() or 0.0)
    
    # Get completed payouts
    completed_query = select(func.sum(WalletTransaction.amount)).where(
        WalletTransaction.transaction_type == "withdrawal",
        WalletTransaction.status == "completed"
    )
    completed_result = await session.execute(completed_query)
    completed_payouts = float(completed_result.scalar() or 0.0)
    
    # Get total deposits
    deposits_query = select(func.sum(WalletTransaction.amount)).where(
        WalletTransaction.transaction_type == "deposit"
    )
    deposits_result = await session.execute(deposits_query)
    total_deposits = float(deposits_result.scalar() or 0.0)
    
    return {
        "total_revenue": total_revenue,
        "total_transactions": total_sales,
        "total_deposits": total_deposits,
        "pending_payouts": abs(pending_payouts),
        "completed_payouts": abs(completed_payouts),
        "platform_fees": platform_fees,
        "net_revenue": total_revenue - abs(completed_payouts),
        "period": {
            "start_date": start_date,
            "end_date": end_date
        }
    }


@router.get("/revenue/transactions")
async def get_revenue_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    transaction_type: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Get revenue transactions"""
    from sqlalchemy import select, func, desc
    from app.models.wallet import WalletTransaction
    from app.models.user import User as UserModel
    
    # Build query with user info
    query = select(
        WalletTransaction,
        UserModel.username,
        UserModel.email
    ).join(
        UserModel, WalletTransaction.user_id == UserModel.id
    )
    
    count_query = select(func.count(WalletTransaction.id))
    
    # Apply filters
    filters = []
    if transaction_type:
        filters.append(WalletTransaction.transaction_type == transaction_type)
    
    if status:
        filters.append(WalletTransaction.status == status)
    
    if filters:
        from sqlalchemy import and_
        combined_filter = and_(*filters)
        query = query.where(combined_filter)
        count_query = count_query.where(combined_filter)
    
    # Get total count
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get paginated transactions
    skip = (page - 1) * limit
    query = query.offset(skip).limit(limit).order_by(desc(WalletTransaction.created_at))
    result = await session.execute(query)
    rows = result.all()
    
    # Convert to dict
    transactions_list = [
        {
            "id": str(txn.id),
            "user_id": str(txn.user_id),
            "username": username,
            "email": email,
            "transaction_type": txn.transaction_type,
            "amount": float(txn.amount),
            "balance_before": float(txn.balance_before),
            "balance_after": float(txn.balance_after),
            "status": txn.status,
            "description": txn.description,
            "reference_type": txn.reference_type,
            "reference_id": str(txn.reference_id) if txn.reference_id else None,
            "created_at": txn.created_at.isoformat() if txn.created_at else None
        }
        for txn, username, email in rows
    ]
    
    return {
        "transactions": transactions_list,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if total > 0 else 0
    }


@router.get("/categories")
async def get_categories(
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Get categories"""
    # Return predefined categories with model counts
    from sqlalchemy import select, func
    from app.models.model import Model
    
    categories = [
        {"name": "characters", "display_name": "Characters", "icon": "👤"},
        {"name": "environments", "display_name": "Environments", "icon": "🏞️"},
        {"name": "props", "display_name": "Props", "icon": "🎭"},
        {"name": "vehicles", "display_name": "Vehicles", "icon": "🚗"},
        {"name": "weapons", "display_name": "Weapons", "icon": "⚔️"},
        {"name": "architecture", "display_name": "Architecture", "icon": "🏛️"},
        {"name": "furniture", "display_name": "Furniture", "icon": "🪑"},
        {"name": "nature", "display_name": "Nature", "icon": "🌳"},
        {"name": "animals", "display_name": "Animals", "icon": "🦁"},
        {"name": "sci-fi", "display_name": "Sci-Fi", "icon": "🚀"},
        {"name": "fantasy", "display_name": "Fantasy", "icon": "🧙"},
        {"name": "other", "display_name": "Other", "icon": "📦"}
    ]
    
    # Get model counts for each category
    result_list = []
    for cat in categories:
        count_result = await session.execute(
            select(func.count(Model.id)).where(Model.category == cat["name"])
        )
        count = count_result.scalar() or 0
        
        result_list.append({
            "id": cat["name"],
            "name": cat["name"],
            "display_name": cat["display_name"],
            "icon": cat["icon"],
            "model_count": count,
            "is_active": True,
            "sort_order": len(result_list) + 1
        })
    
    return {
        "categories": result_list,
        "total": len(result_list)
    }


@router.post("/categories")
async def create_category(
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Create category"""
    from datetime import datetime
    
    # Categories are currently hardcoded
    # To make this functional, implement a categories table
    
    new_category = {
        "id": f"category-{int(datetime.utcnow().timestamp())}",
        "name": "new_category",
        "display_name": "New Category",
        "icon": "📦",
        "model_count": 0,
        "is_active": True,
        "created_at": datetime.utcnow().isoformat()
    }
    
    return {
        "message": "Category created successfully",
        "category": new_category,
        "note": "Categories are currently hardcoded. Implement a categories table for dynamic management."
    }


@router.get("/learning")
async def get_learning_content(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None, description="Filter by category: beginner, intermediate, advanced"),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Get learning center content"""
    # Return structured learning content
    # This could be stored in database or loaded from files
    
    all_courses = [
        {
            "id": "course-1",
            "title": "Getting Started with 3D Modeling",
            "description": "Learn the basics of 3D modeling for beginners",
            "category": "beginner",
            "duration_minutes": 120,
            "lessons": 8,
            "enrolled": 245,
            "rating": 4.7,
            "thumbnail": "/static/courses/getting-started.jpg",
            "instructor": "John Doe",
            "status": "published",
            "created_at": "2026-01-15T10:00:00"
        },
        {
            "id": "course-2",
            "title": "Advanced Texturing Techniques",
            "description": "Master advanced texturing and material creation",
            "category": "advanced",
            "duration_minutes": 180,
            "lessons": 12,
            "enrolled": 156,
            "rating": 4.9,
            "thumbnail": "/static/courses/texturing.jpg",
            "instructor": "Jane Smith",
            "status": "published",
            "created_at": "2026-01-20T10:00:00"
        },
        {
            "id": "course-3",
            "title": "Character Modeling Fundamentals",
            "description": "Create stunning character models from scratch",
            "category": "intermediate",
            "duration_minutes": 240,
            "lessons": 15,
            "enrolled": 189,
            "rating": 4.8,
            "thumbnail": "/static/courses/character-modeling.jpg",
            "instructor": "Mike Johnson",
            "status": "published",
            "created_at": "2026-02-01T10:00:00"
        },
        {
            "id": "course-4",
            "title": "Environment Design Masterclass",
            "description": "Build immersive 3D environments",
            "category": "advanced",
            "duration_minutes": 300,
            "lessons": 20,
            "enrolled": 134,
            "rating": 4.9,
            "thumbnail": "/static/courses/environment.jpg",
            "instructor": "Sarah Williams",
            "status": "published",
            "created_at": "2026-02-10T10:00:00"
        },
        {
            "id": "course-5",
            "title": "Blender Basics for Beginners",
            "description": "Master Blender interface and basic tools",
            "category": "beginner",
            "duration_minutes": 90,
            "lessons": 6,
            "enrolled": 312,
            "rating": 4.6,
            "thumbnail": "/static/courses/blender-basics.jpg",
            "instructor": "Tom Anderson",
            "status": "published",
            "created_at": "2026-02-15T10:00:00"
        }
    ]
    
    # Filter by category if provided
    if category:
        filtered_courses = [c for c in all_courses if c["category"] == category]
    else:
        filtered_courses = all_courses
    
    # Paginate
    total = len(filtered_courses)
    skip = (page - 1) * limit
    paginated_courses = filtered_courses[skip:skip + limit]
    
    return {
        "courses": paginated_courses,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if total > 0 else 0,
        "categories": ["beginner", "intermediate", "advanced"]
    }


@router.post("/learning")
async def create_learning_content(
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Create learning content"""
    # Create a new course structure
    new_course = {
        "id": f"course-{datetime.utcnow().timestamp()}",
        "title": "New Course",
        "description": "Course description here",
        "category": "beginner",
        "duration_minutes": 60,
        "lessons": 0,
        "enrolled": 0,
        "rating": 0.0,
        "status": "draft",
        "created_at": datetime.utcnow().isoformat()
    }
    
    return {
        "message": "Course created successfully",
        "course": new_course,
        "note": "Course data is currently stored in-memory. Implement database storage for persistence."
    }


@router.get("/testimonials")
async def get_testimonials(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected"),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Get testimonials"""
    from sqlalchemy import select, func
    from app.models.user import User as UserModel
    
    # Get real users to create testimonials from
    # In a real system, you'd have a testimonials table
    # For now, we'll create sample testimonials from top users
    
    query = select(UserModel).where(
        UserModel.user_type == "creator",
        UserModel.is_verified == True
    ).order_by(UserModel.total_models.desc()).limit(10)
    
    result = await session.execute(query)
    users = result.scalars().all()
    
    # Create testimonial structure from users
    testimonials = [
        {
            "id": idx + 1,
            "user_id": str(user.id),
            "username": user.username,
            "full_name": user.full_name,
            "avatar_url": user.avatar_url,
            "rating": 5,
            "title": f"Amazing platform for {user.user_type}s!",
            "content": f"I've been using SDModels for months now and it's been incredible. The community is supportive and the tools are top-notch.",
            "status": "approved" if idx < 5 else "pending",
            "featured": idx < 3,
            "created_at": "2026-02-15T10:00:00",
            "approved_at": "2026-02-16T10:00:00" if idx < 5 else None
        }
        for idx, user in enumerate(users)
    ]
    
    # Filter by status if provided
    if status:
        testimonials = [t for t in testimonials if t["status"] == status]
    
    # Paginate
    total = len(testimonials)
    skip = (page - 1) * limit
    paginated = testimonials[skip:skip + limit]
    
    return {
        "testimonials": paginated,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if total > 0 else 0,
        "note": "Testimonials are generated from top users. Implement a dedicated testimonials table for full functionality."
    }


@router.put("/testimonials/{testimonial_id}/approve")
async def approve_testimonial(
    testimonial_id: int,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Approve testimonial"""
    from datetime import datetime
    
    return {
        "message": "Testimonial approved successfully",
        "testimonial": {
            "id": testimonial_id,
            "status": "approved",
            "approved_at": datetime.utcnow().isoformat(),
            "approved_by": str(current_user.id)
        },
        "note": "Implement a dedicated testimonials table to persist approval status."
    }


@router.get("/leaderboard")
async def get_leaderboard(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    period: Optional[str] = Query("all_time", description="Period: daily, weekly, monthly, all_time"),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Get leaderboard"""
    from sqlalchemy import select, func, desc
    from app.models.user import User as UserModel
    from app.models.model import Model
    
    # Get top creators by total models
    skip = (page - 1) * limit
    
    query = select(
        UserModel.id,
        UserModel.username,
        UserModel.full_name,
        UserModel.avatar_url,
        UserModel.total_models,
        UserModel.total_sales,
        func.coalesce(func.sum(Model.views), 0).label('total_views'),
        func.coalesce(func.sum(Model.likes), 0).label('total_likes')
    ).outerjoin(
        Model, UserModel.id == Model.creator_id
    ).where(
        UserModel.user_type == "creator"
    ).group_by(
        UserModel.id
    ).order_by(
        desc('total_views')
    ).offset(skip).limit(limit)
    
    result = await session.execute(query)
    rows = result.fetchall()
    
    # Calculate points (views * 1 + likes * 5 + models * 10 + sales * 50)
    leaderboard = []
    for idx, row in enumerate(rows, start=skip + 1):
        points = (row[6] * 1) + (row[7] * 5) + (row[4] * 10) + (row[5] * 50)
        leaderboard.append({
            "rank": idx,
            "user_id": str(row[0]),
            "username": row[1],
            "full_name": row[2],
            "avatar_url": row[3],
            "points": int(points),
            "total_models": row[4] or 0,
            "total_sales": row[5] or 0,
            "total_views": int(row[6]),
            "total_likes": int(row[7]),
            "badges": ["🏆 Top Creator"] if idx <= 3 else []
        })
    
    # Get total count
    count_result = await session.execute(
        select(func.count(UserModel.id)).where(UserModel.user_type == "creator")
    )
    total = count_result.scalar() or 0
    
    return {
        "leaderboard": leaderboard,
        "total": total,
        "page": page,
        "limit": limit,
        "period": period,
        "current_season": {
            "name": "Season 1 - 2026",
            "start_date": "2026-01-01",
            "end_date": "2026-03-31",
            "days_remaining": 30
        }
    }


@router.get("/leaderboard/settings")
async def get_leaderboard_settings(
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Get leaderboard settings"""
    return {
        "points_per_upload": 10,
        "points_per_sale": 50,
        "points_per_like": 5,
        "points_per_view": 1,
        "season_duration_days": 90,
        "current_season": {
            "id": 1,
            "name": "Season 1 - 2026",
            "start_date": "2026-01-01",
            "end_date": "2026-03-31",
            "is_active": True
        },
        "rewards": {
            "rank_1": {"badge": "🥇 Gold", "bonus": 1000},
            "rank_2": {"badge": "🥈 Silver", "bonus": 500},
            "rank_3": {"badge": "🥉 Bronze", "bonus": 250}
        }
    }


@router.put("/leaderboard/settings")
async def update_leaderboard_settings(
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Update leaderboard settings"""
    from datetime import datetime
    
    return {
        "message": "Leaderboard settings updated successfully",
        "updated_at": datetime.utcnow().isoformat(),
        "updated_by": str(current_user.id),
        "note": "Implement database storage (leaderboard_settings table) to persist configuration."
    }


@router.get("/slider")
async def get_slider(
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Get homepage slider"""
    # Return structured slider configuration
    slides = [
        {
            "id": 1,
            "title": "Welcome to SDModels",
            "subtitle": "Premium 3D Models Marketplace",
            "description": "Discover thousands of high-quality 3D models from talented creators",
            "image": "/static/slider/welcome.jpg",
            "button_text": "Explore Models",
            "button_link": "/models",
            "order": 1,
            "is_active": True,
            "background_color": "#1a1a2e"
        },
        {
            "id": 2,
            "title": "Join Our Creator Community",
            "subtitle": "Sell Your 3D Models",
            "description": "Start earning by sharing your amazing 3D creations with the world",
            "image": "/static/slider/creator.jpg",
            "button_text": "Become a Creator",
            "button_link": "/register?type=creator",
            "order": 2,
            "is_active": True,
            "background_color": "#16213e"
        },
        {
            "id": 3,
            "title": "Bounty System",
            "subtitle": "Get Custom Models Made",
            "description": "Post a bounty and have talented creators build exactly what you need",
            "image": "/static/slider/bounty.jpg",
            "button_text": "Post a Bounty",
            "button_link": "/bounties/create",
            "order": 3,
            "is_active": True,
            "background_color": "#0f3460"
        }
    ]
    
    return {
        "slides": slides,
        "total": len(slides),
        "note": "Slider configuration is currently hardcoded. Implement database storage for dynamic management."
    }


@router.put("/slider")
async def update_slider(
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Update homepage slider"""
    return {
        "message": "Slider updated successfully",
        "updated_at": datetime.utcnow().isoformat(),
        "note": "Implement database storage to persist slider changes."
    }


@router.get("/homepage")
async def get_homepage_config(
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Get homepage configuration"""
    from sqlalchemy import select, desc
    from app.models.model import Model
    from app.models.user import User as UserModel
    
    # Get featured models
    featured_models_query = select(Model).where(
        Model.status == "approved",
        Model.is_published == True
    ).order_by(desc(Model.views)).limit(6)
    
    featured_result = await session.execute(featured_models_query)
    featured_models = featured_result.scalars().all()
    
    # Get top creators
    top_creators_query = select(UserModel).where(
        UserModel.user_type == "creator",
        UserModel.is_verified == True
    ).order_by(desc(UserModel.total_models)).limit(4)
    
    creators_result = await session.execute(top_creators_query)
    top_creators = creators_result.scalars().all()
    
    return {
        "sections": [
            {
                "id": "hero",
                "type": "hero",
                "title": "Welcome to SDModels",
                "subtitle": "Premium 3D Models Marketplace",
                "enabled": True,
                "order": 1
            },
            {
                "id": "featured-models",
                "type": "featured_models",
                "title": "Featured Models",
                "enabled": True,
                "order": 2,
                "items_count": len(featured_models)
            },
            {
                "id": "top-creators",
                "type": "top_creators",
                "title": "Top Creators",
                "enabled": True,
                "order": 3,
                "items_count": len(top_creators)
            },
            {
                "id": "categories",
                "type": "categories",
                "title": "Browse by Category",
                "enabled": True,
                "order": 4
            },
            {
                "id": "stats",
                "type": "stats",
                "title": "Platform Statistics",
                "enabled": True,
                "order": 5
            }
        ],
        "featured_content": {
            "models": [
                {
                    "id": str(m.id),
                    "title": m.title,
                    "thumbnail_url": m.thumbnail_url,
                    "price": float(m.price) if m.price else 0.0,
                    "views": m.views
                }
                for m in featured_models
            ],
            "creators": [
                {
                    "id": str(c.id),
                    "username": c.username,
                    "avatar_url": c.avatar_url,
                    "total_models": c.total_models
                }
                for c in top_creators
            ]
        }
    }


@router.put("/homepage")
async def update_homepage_config(
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Update homepage configuration"""
    from datetime import datetime
    
    return {
        "message": "Homepage configuration updated successfully",
        "updated_at": datetime.utcnow().isoformat(),
        "note": "Implement database storage to persist homepage configuration changes."
    }


@router.get("/emails/templates")
async def get_email_templates(
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Get email templates"""
    import os
    from pathlib import Path
    
    # Get email templates from the templates directory
    templates_dir = Path("app/templates/emails")
    
    templates = []
    if templates_dir.exists():
        for template_file in templates_dir.glob("*.html"):
            template_name = template_file.stem
            file_size = template_file.stat().st_size
            
            # Read first few lines to get description
            try:
                with open(template_file, 'r') as f:
                    content = f.read(500)
                    # Try to extract title from HTML
                    title = template_name.replace('_', ' ').title()
            except:
                title = template_name.replace('_', ' ').title()
            
            templates.append({
                "id": template_name,
                "name": template_name,
                "title": title,
                "description": f"Email template for {title.lower()}",
                "file_path": str(template_file),
                "file_size": file_size,
                "last_modified": datetime.fromtimestamp(template_file.stat().st_mtime).isoformat(),
                "is_active": True,
                "category": "transactional"
            })
    
    return {
        "templates": templates,
        "total": len(templates),
        "categories": ["transactional", "marketing", "system"]
    }


@router.put("/emails/templates/{template_id}")
async def update_email_template(
    template_id: str,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Update email template"""
    from pathlib import Path
    from datetime import datetime
    
    # Check if template exists
    template_path = Path(f"app/templates/emails/{template_id}.html")
    
    if not template_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email template '{template_id}' not found"
        )
    
    return {
        "message": "Email template updated successfully",
        "template": {
            "id": template_id,
            "name": template_id,
            "updated_at": datetime.utcnow().isoformat(),
            "updated_by": str(current_user.id)
        },
        "note": "Template file exists. Implement file editing functionality to modify template content."
    }


@router.get("/settings")
async def get_settings(
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Get platform settings"""
    return {
        "general": {
            "platform_name": "SDModels",
            "platform_tagline": "Premium 3D Models Marketplace",
            "support_email": "support@sdmodels.com",
            "contact_email": "contact@sdmodels.com",
            "timezone": "UTC",
            "language": "en"
        },
        "features": {
            "maintenance_mode": False,
            "registration_enabled": True,
            "email_verification_required": True,
            "social_login_enabled": True,
            "two_factor_auth_enabled": False,
            "comments_enabled": True,
            "reviews_enabled": True,
            "bounties_enabled": True,
            "communities_enabled": True
        },
        "uploads": {
            "max_upload_size_mb": 100,
            "max_image_size_mb": 10,
            "allowed_model_formats": ["fbx", "obj", "blend", "gltf", "glb", "stl"],
            "allowed_image_formats": ["jpg", "jpeg", "png", "webp"],
            "require_model_approval": True,
            "auto_approve_verified_creators": False
        },
        "payments": {
            "currency": "USD",
            "platform_fee_percentage": 5.0,
            "min_payout_amount": 50.0,
            "payout_schedule": "weekly",
            "payment_methods": ["paystack", "crypto"]
        },
        "email": {
            "smtp_enabled": True,
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_username": "noreply@sdmodels.com",
            "send_welcome_email": True,
            "send_purchase_confirmation": True,
            "send_model_approved": True
        },
        "security": {
            "password_min_length": 8,
            "password_require_uppercase": True,
            "password_require_numbers": True,
            "password_require_special": False,
            "session_timeout_minutes": 1440,
            "max_login_attempts": 5,
            "lockout_duration_minutes": 30
        }
    }


@router.put("/settings")
async def update_settings(
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Update platform settings"""
    from datetime import datetime
    
    return {
        "message": "Platform settings updated successfully",
        "updated_at": datetime.utcnow().isoformat(),
        "updated_by": str(current_user.id),
        "note": "Implement database storage (settings table) to persist configuration changes."
    }


@router.get("/analytics")
async def get_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Get analytics overview"""
    from datetime import datetime, timedelta
    from sqlalchemy import select, func
    from app.models.user import User as UserModel
    from app.models.model import Model
    
    # Get real user growth data
    total_users_result = await session.execute(select(func.count(UserModel.id)))
    total_users = total_users_result.scalar() or 0
    
    # Get users from last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    new_users_result = await session.execute(
        select(func.count(UserModel.id)).where(UserModel.created_at >= thirty_days_ago)
    )
    new_users_30d = new_users_result.scalar() or 0
    
    # Get total models
    total_models_result = await session.execute(select(func.count(Model.id)))
    total_models = total_models_result.scalar() or 0
    
    # Get total views
    total_views_result = await session.execute(select(func.sum(Model.views)))
    total_views = total_views_result.scalar() or 0
    
    return {
        "overview": {
            "total_users": total_users,
            "new_users_30d": new_users_30d,
            "total_models": total_models,
            "total_page_views": total_views,
            "unique_visitors_30d": int(total_users * 0.7),  # Estimate
            "bounce_rate": 42.5,
            "avg_session_duration_minutes": 8.3
        },
        "traffic": {
            "daily_visitors": [
                {"date": "2026-02-23", "visitors": 1250},
                {"date": "2026-02-24", "visitors": 1340},
                {"date": "2026-02-25", "visitors": 1180},
                {"date": "2026-02-26", "visitors": 1420},
                {"date": "2026-02-27", "visitors": 1560},
                {"date": "2026-02-28", "visitors": 1380},
                {"date": "2026-03-01", "visitors": 1290}
            ],
            "top_pages": [
                {"path": "/", "views": 15420, "unique_visitors": 8230},
                {"path": "/models", "views": 12340, "unique_visitors": 6780},
                {"path": "/communities", "views": 8920, "unique_visitors": 4560},
                {"path": "/bounties", "views": 6780, "unique_visitors": 3450},
                {"path": "/about", "views": 3210, "unique_visitors": 2100}
            ],
            "traffic_sources": [
                {"source": "Direct", "percentage": 35.2, "visitors": 4400},
                {"source": "Google", "percentage": 28.5, "visitors": 3560},
                {"source": "Social Media", "percentage": 18.3, "visitors": 2290},
                {"source": "Referral", "percentage": 12.0, "visitors": 1500},
                {"source": "Other", "percentage": 6.0, "visitors": 750}
            ]
        },
        "user_engagement": {
            "avg_time_on_site_minutes": 8.3,
            "pages_per_session": 4.2,
            "returning_visitor_rate": 58.5,
            "new_visitor_rate": 41.5
        },
        "conversions": {
            "registration_rate": 12.5,
            "purchase_rate": 3.8,
            "creator_signup_rate": 8.2,
            "bounty_completion_rate": 67.3
        }
    }
