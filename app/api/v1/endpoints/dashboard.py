from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.core.dependencies import get_current_user, get_current_creator
from app.models.user import User

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get dashboard statistics - returns creator stats for creators, buyer stats for buyers"""
    from sqlalchemy import select, func
    from app.models.model import Model, ModelLike
    from app.models.transaction import Transaction
    from app.models.user import UserFollower
    from app.models.wallet import Wallet
    
    if current_user.user_type in ["creator", "seller", "admin"]:
        # Creator/Seller stats
        # Get models count
        models_result = await session.execute(
            select(func.count()).select_from(Model).where(Model.creator_id == current_user.id)
        )
        models_count = models_result.scalar_one()
        
        # Get total likes
        likes_result = await session.execute(
            select(func.count()).select_from(ModelLike).join(Model).where(Model.creator_id == current_user.id)
        )
        total_likes = likes_result.scalar_one()
        
        # Get total downloads (transactions/sales)
        downloads_result = await session.execute(
            select(func.count()).select_from(Transaction).where(Transaction.seller_id == current_user.id)
        )
        total_downloads = downloads_result.scalar_one()
        
        # Get total revenue from BOTH model sales AND bounty earnings
        # 1. Model sales revenue (from Transaction table)
        model_revenue_result = await session.execute(
            select(func.sum(Transaction.seller_amount)).select_from(Transaction).where(Transaction.seller_id == current_user.id)
        )
        model_revenue = model_revenue_result.scalar_one()
        model_revenue = float(model_revenue) if model_revenue else 0.0
        
        # 2. Bounty earnings (from Wallet table - total_earned)
        wallet_result = await session.execute(
            select(Wallet).where(Wallet.user_id == current_user.id)
        )
        wallet = wallet_result.scalar_one_or_none()
        bounty_revenue = float(wallet.total_earned) if wallet else 0.0
        
        # Total revenue = model sales + bounty earnings
        total_revenue = model_revenue + bounty_revenue
        
        # Get followers count
        followers_result = await session.execute(
            select(func.count()).select_from(UserFollower).where(UserFollower.following_id == current_user.id)
        )
        followers_count = followers_result.scalar_one()
        
        return {
            "total_views": 0,  # Views tracking not implemented yet
            "total_likes": total_likes,
            "total_downloads": total_downloads,
            "total_revenue": total_revenue,
            "models_count": models_count,
            "followers_count": followers_count
        }
    else:
        # Buyer stats
        # Get purchases count
        purchases_result = await session.execute(
            select(func.count()).select_from(Transaction).where(Transaction.buyer_id == current_user.id)
        )
        purchases_count = purchases_result.scalar_one()
        
        # Get total spent
        spent_result = await session.execute(
            select(func.sum(Transaction.amount)).select_from(Transaction).where(Transaction.buyer_id == current_user.id)
        )
        total_spent = spent_result.scalar_one()
        total_spent = float(total_spent) if total_spent else 0.0
        
        # Get following count
        following_result = await session.execute(
            select(func.count()).select_from(UserFollower).where(UserFollower.follower_id == current_user.id)
        )
        following_count = following_result.scalar_one()
        
        return {
            "purchases_count": purchases_count,
            "total_spent": total_spent,
            "following_count": following_count,
            "models_count": 0,
            "total_revenue": 0.0,
            "followers_count": 0
        }


@router.get("/recent-activity")
async def get_recent_activity(
    current_user: User = Depends(get_current_creator),
    session: AsyncSession = Depends(get_session)
):
    """Get recent activity"""
    return {"activities": []}


@router.get("/sales-chart")
async def get_sales_chart(
    period: str = Query("month", regex="^(week|month|year)$"),
    current_user: User = Depends(get_current_creator),
    session: AsyncSession = Depends(get_session)
):
    """Get sales chart data"""
    return {"data": []}


@router.get("/models")
async def get_dashboard_models(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_creator),
    session: AsyncSession = Depends(get_session)
):
    """Get creator's models"""
    from sqlalchemy import select, func
    from app.models.model import Model
    from app.schemas.model import ModelResponse
    
    # Build query
    query = select(Model).where(Model.creator_id == current_user.id)
    
    if status:
        query = query.where(Model.status == status)
    
    # Get total count
    count_query = select(func.count()).select_from(Model).where(Model.creator_id == current_user.id)
    if status:
        count_query = count_query.where(Model.status == status)
    
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()
    
    # Get paginated results
    query = query.offset((page - 1) * limit).limit(limit).order_by(Model.created_at.desc())
    result = await session.execute(query)
    models = result.scalars().all()
    
    return {
        "models": [ModelResponse.model_validate(model) for model in models],
        "total": total,
        "page": page,
        "limit": limit
    }


@router.get("/revenue")
async def get_revenue(
    period: str = Query("month", regex="^(week|month|year|all)$"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get revenue data - only for creators"""
    from sqlalchemy import select, func
    from app.models.transaction import Transaction
    from datetime import datetime, timedelta
    
    # Only creators/sellers have revenue
    if current_user.user_type not in ["creator", "seller", "admin"]:
        return {
            "total_revenue": 0.0,
            "platform_fees": 0.0,
            "net_revenue": 0.0,
            "pending_payout": 0.0
        }
    
    # Calculate date filter
    now = datetime.utcnow()
    if period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    elif period == "year":
        start_date = now - timedelta(days=365)
    else:  # all
        start_date = datetime(2000, 1, 1)
    
    # Get total revenue (gross amount)
    revenue_query = select(func.sum(Transaction.amount)).select_from(Transaction).where(
        Transaction.seller_id == current_user.id,
        Transaction.created_at >= start_date
    )
    revenue_result = await session.execute(revenue_query)
    total_revenue = revenue_result.scalar_one()
    total_revenue = float(total_revenue) if total_revenue else 0.0
    
    # Get platform fees
    fees_query = select(func.sum(Transaction.platform_fee)).select_from(Transaction).where(
        Transaction.seller_id == current_user.id,
        Transaction.created_at >= start_date
    )
    fees_result = await session.execute(fees_query)
    platform_fees = fees_result.scalar_one()
    platform_fees = float(platform_fees) if platform_fees else 0.0
    
    # Net revenue is already calculated in seller_amount
    net_query = select(func.sum(Transaction.seller_amount)).select_from(Transaction).where(
        Transaction.seller_id == current_user.id,
        Transaction.created_at >= start_date
    )
    net_result = await session.execute(net_query)
    net_revenue = net_result.scalar_one()
    net_revenue = float(net_revenue) if net_revenue else 0.0
    
    return {
        "total_revenue": total_revenue,
        "platform_fees": platform_fees,
        "net_revenue": net_revenue,
        "pending_payout": 0.0  # Payout system not implemented yet
    }


@router.get("/transactions")
async def get_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get transaction history - shows sales for creators, purchases for buyers"""
    from sqlalchemy import select, func
    from app.models.transaction import Transaction
    
    if current_user.user_type in ["creator", "seller", "admin"]:
        # Get seller transactions
        count_query = select(func.count()).select_from(Transaction).where(Transaction.seller_id == current_user.id)
        total_result = await session.execute(count_query)
        total = total_result.scalar_one()
        
        # Get paginated transactions
        query = select(Transaction).where(Transaction.seller_id == current_user.id).offset((page - 1) * limit).limit(limit).order_by(Transaction.created_at.desc())
        result = await session.execute(query)
        transactions = result.scalars().all()
    else:
        # Get buyer transactions
        count_query = select(func.count()).select_from(Transaction).where(Transaction.buyer_id == current_user.id)
        total_result = await session.execute(count_query)
        total = total_result.scalar_one()
        
        # Get paginated transactions
        query = select(Transaction).where(Transaction.buyer_id == current_user.id).offset((page - 1) * limit).limit(limit).order_by(Transaction.created_at.desc())
        result = await session.execute(query)
        transactions = result.scalars().all()
    
    return {
        "transactions": [
            {
                "id": t.id,
                "buyer_id": t.buyer_id,
                "seller_id": t.seller_id,
                "model_id": t.model_id,
                "amount": float(t.amount),
                "seller_amount": float(t.seller_amount),
                "platform_fee": float(t.platform_fee),
                "payment_method": t.payment_method,
                "payment_status": t.payment_status,
                "transaction_id": t.transaction_id,
                "created_at": t.created_at,
                "completed_at": t.completed_at
            } for t in transactions
        ],
        "total": total,
        "page": page,
        "limit": limit
    }


@router.get("/payouts")
async def get_payouts(
    current_user: User = Depends(get_current_creator),
    session: AsyncSession = Depends(get_session)
):
    """Get payout history"""
    return {"payouts": []}


@router.post("/request-payout")
async def request_payout(
    amount: float,
    current_user: User = Depends(get_current_creator),
    session: AsyncSession = Depends(get_session)
):
    """Request payout"""
    return {"message": "Payout requested", "payout_id": 1}


@router.get("/followers")
async def get_dashboard_followers(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get followers list"""
    from sqlalchemy import select, func
    from app.models.user import UserFollower
    from app.schemas.user import UserResponse
    
    # Get total count
    count_query = select(func.count()).select_from(UserFollower).where(UserFollower.following_id == current_user.id)
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()
    
    # Get paginated followers
    query = select(User).join(UserFollower, UserFollower.follower_id == User.id).where(
        UserFollower.following_id == current_user.id
    ).offset((page - 1) * limit).limit(limit).order_by(UserFollower.created_at.desc())
    result = await session.execute(query)
    followers = result.scalars().all()
    
    return {
        "followers": [UserResponse.model_validate(f) for f in followers],
        "total": total,
        "page": page,
        "limit": limit
    }


@router.get("/financials/balance")
async def get_financial_balance(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get user financial balance - includes both model sales and bounty earnings"""
    from sqlalchemy import select, func
    from app.models.transaction import Transaction
    from app.models.wallet import Wallet, WalletTransaction
    
    # Get wallet data (for all users)
    wallet_query = select(Wallet).where(Wallet.user_id == current_user.id)
    wallet_result = await session.execute(wallet_query)
    wallet = wallet_result.scalar_one_or_none()
    
    # Get total earnings (for creators/sellers)
    if current_user.user_type in ["creator", "seller"]:
        if wallet:
            # Wallet total_earned includes bounty earnings
            total_earnings = float(wallet.total_earned)
            available_balance = float(wallet.available_balance)
            pending_balance = float(wallet.held_balance)
        else:
            # No wallet yet, check old transaction system
            earnings_query = select(func.sum(Transaction.seller_amount)).select_from(Transaction).where(
                Transaction.seller_id == current_user.id
            )
            earnings_result = await session.execute(earnings_query)
            total_earnings = earnings_result.scalar_one()
            total_earnings = float(total_earnings) if total_earnings else 0.0
            available_balance = total_earnings
            pending_balance = 0.0
        
        # Calculate total platform fees (model sales + bounty fees)
        # Model sales fees
        model_fees_query = select(func.sum(Transaction.platform_fee)).select_from(Transaction).where(
            Transaction.seller_id == current_user.id
        )
        model_fees_result = await session.execute(model_fees_query)
        model_fees = model_fees_result.scalar_one()
        model_fees = float(model_fees) if model_fees else 0.0
        
        # Bounty fees (7.5% of bounty earnings)
        bounty_earnings_query = select(func.sum(WalletTransaction.amount)).select_from(WalletTransaction).where(
            WalletTransaction.user_id == current_user.id,
            WalletTransaction.transaction_type.in_(['bounty_payment', 'milestone_payment'])
        )
        bounty_earnings_result = await session.execute(bounty_earnings_query)
        bounty_earnings = bounty_earnings_result.scalar_one()
        bounty_earnings = float(bounty_earnings) if bounty_earnings else 0.0
        
        # Calculate bounty fees (reverse calculate from net amount)
        bounty_fees = (bounty_earnings * 0.075) / 0.925 if bounty_earnings > 0 else 0.0
        
        total_fees = model_fees + bounty_fees
    else:
        # For buyers/clients - show wallet balance
        if wallet:
            available_balance = float(wallet.available_balance)
            pending_balance = float(wallet.held_balance)
            total_earnings = float(wallet.total_deposited) - float(wallet.total_withdrawn)
        else:
            available_balance = 0.0
            pending_balance = 0.0
            total_earnings = 0.0
        
        total_fees = 0.0
    
    # Return in frontend-expected format
    return {
        "data": {
            "available": available_balance,
            "pending": pending_balance,
            "total": total_earnings,
            "fees": total_fees
        }
    }


@router.get("/financials/earnings")
async def get_financial_earnings(
    months: int = Query(6, ge=1, le=24),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get monthly earnings data for chart - includes model sales and bounty earnings"""
    from sqlalchemy import select, func, extract
    from app.models.transaction import Transaction
    from app.models.wallet import WalletTransaction
    from datetime import datetime, timedelta
    from calendar import month_abbr
    
    if current_user.user_type not in ["creator", "seller"]:
        # Return empty data for non-creators
        return {"data": []}
    
    # Calculate date range
    now = datetime.utcnow()
    start_date = now - timedelta(days=30 * months)
    
    # Get model sales grouped by month
    model_sales_query = select(
        extract('year', Transaction.created_at).label('year'),
        extract('month', Transaction.created_at).label('month'),
        func.sum(Transaction.seller_amount).label('amount'),
        func.count(Transaction.id).label('count')
    ).where(
        Transaction.seller_id == current_user.id,
        Transaction.created_at >= start_date
    ).group_by('year', 'month')
    
    model_sales_result = await session.execute(model_sales_query)
    model_sales_by_month = {}
    for row in model_sales_result:
        key = f"{int(row.year)}-{int(row.month):02d}"
        model_sales_by_month[key] = {
            'amount': float(row.amount) if row.amount else 0.0,
            'count': int(row.count)
        }
    
    # Get bounty payments grouped by month
    bounty_payments_query = select(
        extract('year', WalletTransaction.created_at).label('year'),
        extract('month', WalletTransaction.created_at).label('month'),
        func.sum(WalletTransaction.amount).label('amount'),
        func.count(WalletTransaction.id).label('count')
    ).where(
        WalletTransaction.user_id == current_user.id,
        WalletTransaction.transaction_type.in_(['bounty_payment', 'milestone_payment']),
        WalletTransaction.created_at >= start_date
    ).group_by('year', 'month')
    
    bounty_payments_result = await session.execute(bounty_payments_query)
    bounty_payments_by_month = {}
    for row in bounty_payments_result:
        key = f"{int(row.year)}-{int(row.month):02d}"
        bounty_payments_by_month[key] = {
            'amount': float(row.amount) if row.amount else 0.0,
            'count': int(row.count)
        }
    
    # Build monthly data for last N months
    earnings_data = []
    for i in range(months):
        month_date = now - timedelta(days=30 * (months - 1 - i))
        month_key = f"{month_date.year}-{month_date.month:02d}"
        
        model_data = model_sales_by_month.get(month_key, {'amount': 0.0, 'count': 0})
        bounty_data = bounty_payments_by_month.get(month_key, {'amount': 0.0, 'count': 0})
        
        earnings_data.append({
            "month": month_abbr[month_date.month],
            "year": month_date.year,
            "amount": model_data['amount'] + bounty_data['amount'],
            "sales_count": model_data['count'],
            "bounties_count": bounty_data['count']
        })
    
    # Return in frontend-expected format
    return {"data": earnings_data}


@router.get("/financials/transactions")
async def get_financial_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    type: Optional[str] = Query(None, regex="^(earning|purchase|payout)$"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get financial transaction history - includes model sales and bounty payments"""
    from sqlalchemy import select, func, union_all
    from app.models.model import Model
    from app.models.transaction import Transaction
    from app.models.wallet import WalletTransaction
    from app.models.bounty import Bounty
    
    if current_user.user_type in ["creator", "seller"]:
        # Get earnings transactions (model sales + bounty payments)
        transactions_list = []
        
        # 1. Get model sales from Transaction table
        model_sales_query = select(Transaction).where(Transaction.seller_id == current_user.id)
        model_sales_result = await session.execute(model_sales_query)
        model_sales = model_sales_result.scalars().all()
        
        for t in model_sales:
            # Get model info
            model_result = await session.execute(
                select(Model.title).where(Model.id == t.model_id)
            )
            model_title = model_result.scalar_one_or_none()
            
            transactions_list.append({
                "id": str(t.id),
                "type": "sale",
                "description": f"Sale of model",
                "model": model_title or "Unknown Model",
                "amount": float(t.seller_amount),  # Amount after platform fee
                "status": "completed" if t.payment_status == "completed" else t.payment_status,
                "created_at": t.created_at.isoformat() if t.created_at else None
            })
        
        # 2. Get bounty payments from WalletTransaction table
        bounty_payments_query = select(WalletTransaction).where(
            WalletTransaction.user_id == current_user.id,
            WalletTransaction.transaction_type.in_(['bounty_payment', 'milestone_payment'])
        )
        bounty_payments_result = await session.execute(bounty_payments_query)
        bounty_payments = bounty_payments_result.scalars().all()
        
        for t in bounty_payments:
            # Extract bounty info from description or reference_id
            bounty_title = "Bounty Completion"
            if t.reference_id:
                bounty_result = await session.execute(
                    select(Bounty.title).where(Bounty.id == t.reference_id)
                )
                bounty_title_result = bounty_result.scalar_one_or_none()
                if bounty_title_result:
                    bounty_title = bounty_title_result
            
            transactions_list.append({
                "id": str(t.id),
                "type": "bounty_payment",
                "description": t.description or "Bounty payment received",
                "model": bounty_title,
                "amount": float(t.amount),
                "status": "completed",
                "created_at": t.created_at.isoformat() if t.created_at else None
            })
        
        # Sort by created_at descending
        transactions_list.sort(key=lambda x: x['created_at'] or '', reverse=True)
        
        # Paginate
        total = len(transactions_list)
        start = (page - 1) * limit
        end = start + limit
        paginated_transactions = transactions_list[start:end]
        
    else:
        # Get purchase transactions (where user is buyer)
        count_query = select(func.count()).select_from(Transaction).where(Transaction.buyer_id == current_user.id)
        total_result = await session.execute(count_query)
        total = total_result.scalar_one()
        
        # Get paginated transactions
        query = select(Transaction).where(Transaction.buyer_id == current_user.id).offset((page - 1) * limit).limit(limit).order_by(Transaction.created_at.desc())
        result = await session.execute(query)
        transactions_db = result.scalars().all()
        
        paginated_transactions = []
        for t in transactions_db:
            # Get model info
            model_result = await session.execute(
                select(Model.title).where(Model.id == t.model_id)
            )
            model_title = model_result.scalar_one_or_none()
            
            paginated_transactions.append({
                "id": str(t.id),
                "type": "purchase",
                "description": f"Purchase of model",
                "model": model_title or "Unknown Model",
                "amount": float(t.amount),
                "status": "completed" if t.payment_status == "completed" else t.payment_status,
                "created_at": t.created_at.isoformat() if t.created_at else None
            })
    
    # Return in frontend-expected format
    return {
        "data": paginated_transactions,
        "total": total,
        "page": page,
        "limit": limit
    }


@router.get("/notifications")
async def get_dashboard_notifications(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get dashboard notifications"""
    return {"notifications": []}


@router.get("/activity")
async def get_dashboard_activity(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get user activity"""
    return {"activities": []}


@router.get("/social/stats")
async def get_social_stats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get social statistics"""
    from sqlalchemy import select, func
    from app.models.user import UserFollower
    from app.models.model import ModelLike, ModelComment
    
    # Get followers count
    followers_result = await session.execute(
        select(func.count()).select_from(UserFollower).where(UserFollower.following_id == current_user.id)
    )
    followers_count = followers_result.scalar_one()
    
    # Get following count
    following_result = await session.execute(
        select(func.count()).select_from(UserFollower).where(UserFollower.follower_id == current_user.id)
    )
    following_count = following_result.scalar_one()
    
    # Get total likes received (if creator/seller)
    if current_user.user_type in ["creator", "seller", "admin"]:
        from app.models.model import Model
        likes_result = await session.execute(
            select(func.count()).select_from(ModelLike).join(Model).where(Model.creator_id == current_user.id)
        )
        likes_received = likes_result.scalar_one()
        
        # Get total comments received
        comments_result = await session.execute(
            select(func.count()).select_from(ModelComment).join(Model).where(Model.creator_id == current_user.id)
        )
        comments_received = comments_result.scalar_one()
    else:
        likes_received = 0
        comments_received = 0
    
    return {
        "followers_count": followers_count,
        "following_count": following_count,
        "likes_received": likes_received,
        "comments_received": comments_received
    }


@router.get("/social/activity")
async def get_social_activity(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get social activity feed"""
    from sqlalchemy import select, func, or_
    from app.models.user import UserFollower
    from app.models.model import Model, ModelLike, ModelComment
    
    # Get users that current user follows
    following_query = select(UserFollower.following_id).where(UserFollower.follower_id == current_user.id)
    following_result = await session.execute(following_query)
    following_ids = [row[0] for row in following_result.fetchall()]
    
    if not following_ids:
        return {
            "activities": [],
            "total": 0,
            "page": page,
            "limit": limit
        }
    
    # Get recent models from followed users
    models_query = select(Model).where(
        Model.creator_id.in_(following_ids),
        Model.status == "approved"
    ).order_by(Model.created_at.desc()).limit(limit)
    
    models_result = await session.execute(models_query)
    models = models_result.scalars().all()
    
    activities = [
        {
            "type": "model_upload",
            "user_id": m.creator_id,
            "model_id": m.id,
            "model_title": m.title,
            "created_at": m.created_at
        } for m in models
    ]
    
    return {
        "activities": activities,
        "total": len(activities),
        "page": page,
        "limit": limit
    }


@router.get("/messages")
async def get_dashboard_messages(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get user messages/conversations"""
    # Messages system not implemented yet
    return {
        "conversations": [],
        "unread_count": 0,
        "total": 0,
        "page": page,
        "limit": limit
    }


@router.get("/settings")
async def get_dashboard_settings(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get user settings"""
    return {
        "notifications": {
            "email_notifications": True,
            "push_notifications": True,
            "marketing_emails": False,
            "new_follower": True,
            "new_comment": True,
            "new_like": True,
            "new_purchase": True
        },
        "privacy": {
            "profile_visibility": "public",
            "show_email": False,
            "show_purchases": False
        },
        "preferences": {
            "language": "en",
            "timezone": "UTC",
            "currency": "USD"
        }
    }


@router.put("/settings")
async def update_dashboard_settings(
    settings: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update user settings"""
    # Settings system not fully implemented yet
    return {
        "message": "Settings updated successfully",
        "settings": settings
    }


@router.get("/settings/profile")
async def get_profile_settings(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get user profile settings"""
    from app.models.user import UserProfile
    from sqlalchemy import select
    
    # Get user profile
    query = select(UserProfile).where(UserProfile.user_id == current_user.id)
    result = await session.execute(query)
    profile = result.scalar_one_or_none()
    
    return {
        "full_name": current_user.full_name,
        "username": current_user.username,
        "bio": current_user.bio,
        "avatar_url": current_user.avatar_url,
        "location": profile.location if profile else None,
        "website": profile.website if profile else None
    }


@router.patch("/settings/profile")
async def update_profile_settings(
    profile_data: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update user profile settings"""
    from app.models.user import UserProfile
    from app.schemas.user import UserResponse
    from sqlalchemy import select
    
    # Update basic profile fields on User model
    basic_fields = ["full_name", "username", "bio", "avatar_url"]
    for field in basic_fields:
        if field in profile_data:
            setattr(current_user, field, profile_data[field])
    
    # Get or create user profile for location and website
    query = select(UserProfile).where(UserProfile.user_id == current_user.id)
    result = await session.execute(query)
    profile = result.scalar_one_or_none()
    
    if not profile:
        # Create new profile
        profile = UserProfile(user_id=current_user.id)
        session.add(profile)
    
    # Update location and website in user_profiles table
    if "location" in profile_data:
        profile.location = profile_data["location"]
    
    if "website" in profile_data:
        profile.website = profile_data["website"]
    
    # Save changes
    await session.commit()
    await session.refresh(current_user)
    await session.refresh(profile)
    
    return {
        "message": "Profile updated successfully",
        "profile": {
            "full_name": current_user.full_name,
            "username": current_user.username,
            "bio": current_user.bio,
            "avatar_url": current_user.avatar_url,
            "location": profile.location,
            "website": profile.website
        }
    }


@router.get("/settings/social")
async def get_social_links(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get user social links"""
    from app.models.user import UserProfile
    from sqlalchemy import select
    
    # Get user profile
    query = select(UserProfile).where(UserProfile.user_id == current_user.id)
    result = await session.execute(query)
    profile = result.scalar_one_or_none()
    
    if not profile:
        return {
            "artstation": None,
            "twitter": None,
            "instagram": None,
            "youtube": None,
            "website": None,
            "portfolio_url": None
        }
    
    return {
        "artstation": profile.artstation,
        "twitter": profile.twitter,
        "instagram": profile.instagram,
        "youtube": profile.youtube,
        "website": profile.website,
        "portfolio_url": profile.portfolio_url
    }


@router.patch("/settings/social")
async def update_social_links(
    social_data: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update user social links"""
    from app.models.user import UserProfile
    from sqlalchemy import select
    
    # Get or create user profile
    query = select(UserProfile).where(UserProfile.user_id == current_user.id)
    result = await session.execute(query)
    profile = result.scalar_one_or_none()
    
    if not profile:
        # Create new profile
        profile = UserProfile(user_id=current_user.id)
        session.add(profile)
    
    # Update social links
    if "artstation" in social_data:
        profile.artstation = social_data["artstation"]
    if "twitter" in social_data:
        profile.twitter = social_data["twitter"]
    if "instagram" in social_data:
        profile.instagram = social_data["instagram"]
    if "youtube" in social_data:
        profile.youtube = social_data["youtube"]
    if "website" in social_data:
        profile.website = social_data["website"]
    if "portfolio_url" in social_data:
        profile.portfolio_url = social_data["portfolio_url"]
    
    await session.commit()
    await session.refresh(profile)
    
    return {
        "message": "Social links updated successfully",
        "social_links": {
            "artstation": profile.artstation,
            "twitter": profile.twitter,
            "instagram": profile.instagram,
            "youtube": profile.youtube,
            "website": profile.website,
            "portfolio_url": profile.portfolio_url
        }
    }


@router.patch("/settings/security")
async def update_security_settings(
    security_data: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update user security settings (password change, 2FA, etc)"""
    from app.core.security import verify_password, get_password_hash
    from app.models.user import UserProfile
    from fastapi import HTTPException, status
    from sqlalchemy import select
    from datetime import datetime
    
    # Check if changing password
    if "current_password" in security_data and "new_password" in security_data:
        # Verify current password
        if not verify_password(security_data["current_password"], current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Validate new password
        if len(security_data["new_password"]) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 8 characters"
            )
        
        # Update password
        current_user.password_hash = get_password_hash(security_data["new_password"])
        
        # Update last password change timestamp
        query = select(UserProfile).where(UserProfile.user_id == current_user.id)
        result = await session.execute(query)
        profile = result.scalar_one_or_none()
        
        if not profile:
            profile = UserProfile(user_id=current_user.id)
            session.add(profile)
        
        profile.last_password_change = datetime.utcnow()
        await session.commit()
        
        return {
            "message": "Password updated successfully"
        }
    
    # Get or create user profile for security settings
    query = select(UserProfile).where(UserProfile.user_id == current_user.id)
    result = await session.execute(query)
    profile = result.scalar_one_or_none()
    
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        session.add(profile)
    
    # Handle 2FA toggle
    if "two_factor_enabled" in security_data:
        profile.two_factor_enabled = security_data["two_factor_enabled"]
        await session.commit()
        await session.refresh(profile)
        
        return {
            "message": "Two-factor authentication setting updated",
            "two_factor_enabled": profile.two_factor_enabled
        }
    
    # Handle biometric scan toggle
    if "biometric_enabled" in security_data:
        profile.biometric_enabled = security_data["biometric_enabled"]
        await session.commit()
        await session.refresh(profile)
        
        return {
            "message": "Biometric authentication setting updated",
            "biometric_enabled": profile.biometric_enabled
        }
    
    return {
        "message": "Security settings updated successfully"
    }


@router.get("/settings/security/status")
async def get_security_status(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get Neural Link security status"""
    from app.models.user import UserProfile
    from sqlalchemy import select
    
    # Get user profile for security settings
    query = select(UserProfile).where(UserProfile.user_id == current_user.id)
    result = await session.execute(query)
    profile = result.scalar_one_or_none()
    
    return {
        "status": "active",
        "two_factor_enabled": profile.two_factor_enabled if profile else False,
        "biometric_enabled": profile.biometric_enabled if profile else False,
        "last_password_change": profile.last_password_change if profile else None,
        "active_sessions_count": 1
    }


@router.get("/settings/security/sessions")
async def get_active_sessions(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get active sessions"""
    # Session management not fully implemented yet
    # Return mock data for now
    return {
        "sessions": [
            {
                "id": 1,
                "device": "Chrome on MacBook Pro",
                "location": "San Francisco, CA",
                "ip_address": "192.168.1.1",
                "last_active": "Active now",
                "is_current": True
            }
        ]
    }


@router.delete("/settings/security/sessions/{session_id}")
async def revoke_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Revoke a session"""
    # Session management not fully implemented yet
    return {
        "message": "Session revoked successfully"
    }


@router.get("/settings/sessions")
async def get_sessions_alias(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get active sessions (alias for /settings/security/sessions)"""
    # Session management not fully implemented yet
    return {
        "sessions": [
            {
                "id": 1,
                "device": "Chrome on MacBook Pro",
                "location": "San Francisco, CA",
                "ip_address": "192.168.1.1",
                "last_active": "Active now",
                "is_current": True
            }
        ]
    }


@router.get("/settings/alerts")
async def get_alert_settings(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get notification/alert preferences"""
    from app.models.user import UserProfile
    from sqlalchemy import select
    
    # Get user profile
    query = select(UserProfile).where(UserProfile.user_id == current_user.id)
    result = await session.execute(query)
    profile = result.scalar_one_or_none()
    
    if not profile:
        # Return defaults if no profile exists
        return {
            "notification_preferences": {
                "email_notifications": True,
                "push_notifications": False
            },
            "alert_types": {
                "new_sales": True,
                "new_reviews": True,
                "new_followers": True,
                "messages": True,
                "platform_updates": False,
                "marketing": False
            }
        }
    
    return {
        "notification_preferences": {
            "email_notifications": profile.email_notifications,
            "push_notifications": profile.push_notifications
        },
        "alert_types": {
            "new_sales": profile.alert_new_sales,
            "new_reviews": profile.alert_new_reviews,
            "new_followers": profile.alert_new_followers,
            "messages": profile.alert_messages,
            "platform_updates": profile.alert_platform_updates,
            "marketing": profile.alert_marketing
        }
    }


@router.patch("/settings/alerts")
async def update_alert_settings(
    alert_data: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update notification/alert preferences"""
    from app.models.user import UserProfile
    from sqlalchemy import select
    
    # Get or create user profile
    query = select(UserProfile).where(UserProfile.user_id == current_user.id)
    result = await session.execute(query)
    profile = result.scalar_one_or_none()
    
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        session.add(profile)
    
    # Update notification preferences
    if "notification_preferences" in alert_data:
        prefs = alert_data["notification_preferences"]
        if "email_notifications" in prefs:
            profile.email_notifications = prefs["email_notifications"]
        if "push_notifications" in prefs:
            profile.push_notifications = prefs["push_notifications"]
    
    # Update alert types
    if "alert_types" in alert_data:
        alerts = alert_data["alert_types"]
        if "new_sales" in alerts:
            profile.alert_new_sales = alerts["new_sales"]
        if "new_reviews" in alerts:
            profile.alert_new_reviews = alerts["new_reviews"]
        if "new_followers" in alerts:
            profile.alert_new_followers = alerts["new_followers"]
        if "messages" in alerts:
            profile.alert_messages = alerts["messages"]
        if "platform_updates" in alerts:
            profile.alert_platform_updates = alerts["platform_updates"]
        if "marketing" in alerts:
            profile.alert_marketing = alerts["marketing"]
    
    await session.commit()
    await session.refresh(profile)
    
    return {
        "message": "Alert preferences updated successfully",
        "preferences": {
            "notification_preferences": {
                "email_notifications": profile.email_notifications,
                "push_notifications": profile.push_notifications
            },
            "alert_types": {
                "new_sales": profile.alert_new_sales,
                "new_reviews": profile.alert_new_reviews,
                "new_followers": profile.alert_new_followers,
                "messages": profile.alert_messages,
                "platform_updates": profile.alert_platform_updates,
                "marketing": profile.alert_marketing
            }
        }
    }


@router.get("/settings/billing")
async def get_billing_settings(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get billing information"""
    from sqlalchemy import select
    from app.models.user import PaymentMethod, UserProfile
    from app.models.transaction import Transaction
    from sqlalchemy import func
    
    # Get payment methods
    payment_methods_query = select(PaymentMethod).where(PaymentMethod.user_id == current_user.id)
    payment_methods_result = await session.execute(payment_methods_query)
    payment_methods_list = payment_methods_result.scalars().all()
    
    payment_methods = []
    for pm in payment_methods_list:
        method_data = {
            "id": pm.id,
            "type": pm.type,
            "is_primary": pm.is_primary
        }
        
        if pm.type == "paypal":
            method_data["email"] = pm.paypal_email
        elif pm.type == "bank_account":
            method_data["last_four"] = pm.account_number_last_four
            method_data["bank_name"] = pm.bank_name
        elif pm.type == "stripe":
            method_data["stripe_account_id"] = pm.stripe_account_id
        
        payment_methods.append(method_data)
    
    # Calculate current rank based on total sales
    total_sales = current_user.total_sales if hasattr(current_user, 'total_sales') else 0
    
    # Get actual transaction count for more accurate ranking
    sales_count_query = select(func.count()).select_from(Transaction).where(Transaction.seller_id == current_user.id)
    sales_count_result = await session.execute(sales_count_query)
    sales_count = sales_count_result.scalar_one()
    
    # Determine rank based on sales count
    if sales_count >= 1000:
        current_rank = "Mythic"
        platform_fee = 5.0
        next_rank = None
        next_rank_fee = None
    elif sales_count >= 501:
        current_rank = "Platinum"
        platform_fee = 5.5
        next_rank = "Mythic"
        next_rank_fee = 5.0
    elif sales_count >= 151:
        current_rank = "Gold Modeller"
        platform_fee = 6.0
        next_rank = "Platinum"
        next_rank_fee = 5.5
    elif sales_count >= 51:
        current_rank = "Silver"
        platform_fee = 7.0
        next_rank = "Gold"
        next_rank_fee = 6.0
    else:
        current_rank = "Bronze"
        platform_fee = 7.5
        next_rank = "Silver"
        next_rank_fee = 7.0
    
    # Get tax information from user profile
    profile_query = select(UserProfile).where(UserProfile.user_id == current_user.id)
    profile_result = await session.execute(profile_query)
    profile = profile_result.scalar_one_or_none()
    
    tax_info = {
        "tax_id": profile.tax_id if profile else None,
        "business_name": profile.business_name if profile else None
    }
    
    return {
        "payment_methods": payment_methods,
        "fee_structure": {
            "current_rank": current_rank,
            "platform_fee": platform_fee,
            "earnings_percentage": 100.0 - platform_fee,
            "next_rank": next_rank,
            "next_rank_fee": next_rank_fee,
            "tiers": [
                {"name": "Bronze", "sales_range": "0-50 sales", "fee": 7.5},
                {"name": "Silver", "sales_range": "51-150 sales", "fee": 7.0},
                {"name": "Gold", "sales_range": "151-500 sales", "fee": 6.0},
                {"name": "Platinum", "sales_range": "501-1000 sales", "fee": 5.5},
                {"name": "Mythic", "sales_range": "1000+ sales", "fee": 5.0}
            ]
        },
        "tax_information": tax_info
    }


@router.post("/settings/billing/payment-methods")
async def add_payment_method(
    payment_data: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Add new payment method"""
    from app.models.user import PaymentMethod
    from sqlalchemy import select
    
    # Create new payment method
    new_method = PaymentMethod(
        user_id=current_user.id,
        type=payment_data.get("type", "paypal"),
        is_primary=False
    )
    
    # Set type-specific fields
    if new_method.type == "paypal":
        new_method.paypal_email = payment_data.get("email")
    elif new_method.type == "bank_account":
        # Store only last 4 digits for security
        account_number = payment_data.get("account_number", "")
        new_method.account_number_last_four = account_number[-4:] if len(account_number) >= 4 else account_number
        new_method.routing_number = payment_data.get("routing_number")
        new_method.account_holder_name = payment_data.get("account_holder_name")
        new_method.bank_name = payment_data.get("bank_name")
    elif new_method.type == "stripe":
        new_method.stripe_account_id = payment_data.get("stripe_account_id")
    
    session.add(new_method)
    await session.commit()
    await session.refresh(new_method)
    
    # Build response
    response_data = {
        "id": new_method.id,
        "type": new_method.type,
        "is_primary": new_method.is_primary
    }
    
    if new_method.type == "paypal":
        response_data["email"] = new_method.paypal_email
    elif new_method.type == "bank_account":
        response_data["last_four"] = new_method.account_number_last_four
        response_data["bank_name"] = new_method.bank_name
    
    return {
        "message": "Payment method added successfully",
        "payment_method": response_data
    }


@router.delete("/settings/billing/payment-methods/{method_id}")
async def remove_payment_method(
    method_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Remove payment method"""
    from app.models.user import PaymentMethod
    from sqlalchemy import select
    from fastapi import HTTPException, status
    
    # Get payment method
    query = select(PaymentMethod).where(
        PaymentMethod.id == method_id,
        PaymentMethod.user_id == current_user.id
    )
    result = await session.execute(query)
    payment_method = result.scalar_one_or_none()
    
    if not payment_method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found"
        )
    
    # Delete payment method
    await session.delete(payment_method)
    await session.commit()
    
    return {
        "message": "Payment method removed successfully"
    }


@router.patch("/settings/billing/payment-methods/{method_id}/primary")
async def set_primary_payment_method(
    method_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Set payment method as primary"""
    from app.models.user import PaymentMethod
    from sqlalchemy import select, update
    from fastapi import HTTPException, status
    
    # Get payment method
    query = select(PaymentMethod).where(
        PaymentMethod.id == method_id,
        PaymentMethod.user_id == current_user.id
    )
    result = await session.execute(query)
    payment_method = result.scalar_one_or_none()
    
    if not payment_method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found"
        )
    
    # Set all other payment methods to non-primary
    await session.execute(
        update(PaymentMethod)
        .where(PaymentMethod.user_id == current_user.id)
        .values(is_primary=False)
    )
    
    # Set this payment method as primary
    payment_method.is_primary = True
    await session.commit()
    
    return {
        "message": "Primary payment method updated successfully"
    }


@router.patch("/settings/billing/tax")
async def update_tax_information(
    tax_data: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update tax information"""
    from app.models.user import UserProfile
    from sqlalchemy import select
    
    # Get or create user profile
    query = select(UserProfile).where(UserProfile.user_id == current_user.id)
    result = await session.execute(query)
    profile = result.scalar_one_or_none()
    
    if not profile:
        # Create new profile
        profile = UserProfile(user_id=current_user.id)
        session.add(profile)
    
    # Update tax information
    if "tax_id" in tax_data:
        profile.tax_id = tax_data["tax_id"]
    if "business_name" in tax_data:
        profile.business_name = tax_data["business_name"]
    
    await session.commit()
    await session.refresh(profile)
    
    return {
        "message": "Tax information updated successfully",
        "tax_info": {
            "tax_id": profile.tax_id,
            "business_name": profile.business_name
        }
    }
