from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.transaction import CartAddRequest, CheckoutRequest
from app.repositories.transaction_repository import TransactionRepository
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/cart")
async def add_to_cart(
    cart_data: CartAddRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Add model to cart"""
    transaction_repo = TransactionRepository(session)
    cart_item = await transaction_repo.add_to_cart(current_user.id, cart_data.model_id)
    return cart_item


@router.post("/cart/apply-coupon")
async def apply_coupon(
    coupon_code: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Apply coupon code to cart"""
    # TODO: Implement coupon validation and application
    return {"message": "Coupon applied", "discount": 10.0}


@router.get("/cart")
async def get_cart(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get user's cart items"""
    transaction_repo = TransactionRepository(session)
    cart_items = await transaction_repo.get_cart(current_user.id)
    return {"cart_items": cart_items}


@router.delete("/cart/{model_id}")
async def remove_from_cart(
    model_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Remove from cart"""
    transaction_repo = TransactionRepository(session)
    success = await transaction_repo.remove_from_cart(current_user.id, model_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found"
        )
    
    return {"message": "Item removed from cart"}


@router.post("/checkout")
async def checkout(
    checkout_data: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Process checkout"""
    # TODO: Implement Stripe payment processing
    return {"message": "Checkout successful", "transaction_id": "TXN-123"}


@router.get("/purchases")
async def get_purchases(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get user's purchased models with full model details"""
    from sqlalchemy import select
    from app.models.model import Model
    from app.models.transaction import Purchase
    from app.schemas.model import ModelResponse
    
    skip = (page - 1) * limit
    
    # Join Purchase with Model to get full model details
    # Only return models purchased by current user
    result = await session.execute(
        select(Purchase, Model)
        .join(Model, Purchase.model_id == Model.id)
        .where(Purchase.user_id == current_user.id)
        .order_by(Purchase.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    
    purchases_with_models = []
    for purchase, model in result.all():
        purchases_with_models.append({
            "purchase_id": purchase.id,
            "purchased_at": purchase.created_at,
            "download_count": purchase.download_count,
            "download_limit": purchase.download_limit,
            "model": ModelResponse.model_validate(model)
        })
    
    return {
        "purchases": purchases_with_models,
        "page": page,
        "limit": limit
    }


@router.get("/purchases/{model_id}/download")
async def get_download_link(
    model_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get download link for purchased model"""
    transaction_repo = TransactionRepository(session)
    purchase = await transaction_repo.get_purchase(current_user.id, model_id)
    
    if not purchase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase not found"
        )
    
    if purchase.download_count >= purchase.download_limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Download limit reached"
        )
    
    # TODO: Generate signed URL for download
    await transaction_repo.increment_download_count(purchase.id)
    
    return {
        "download_url": "https://cdn.sdmodels.com/models/signed-url",
        "expires_at": "2024-02-17T00:00:00Z"
    }


@router.get("/history")
async def get_transaction_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get transaction history"""
    skip = (page - 1) * limit
    transaction_repo = TransactionRepository(session)
    transactions = await transaction_repo.get_user_transactions(current_user.id, skip, limit)
    
    return {
        "transactions": transactions,
        "page": page,
        "limit": limit
    }
