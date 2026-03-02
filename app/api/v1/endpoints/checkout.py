from uuid import UUID, uuid4
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_session
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.model import Model
from app.schemas.transaction import CheckoutRequest
from app.services.earnings_service import EarningsService
from app.repositories.transaction_repository import TransactionRepository

router = APIRouter()


@router.get("/payment-methods")
async def get_payment_methods(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get available payment methods"""
    return {
        "methods": [
            {"id": "card", "name": "Credit/Debit Card", "enabled": True},
            {"id": "paypal", "name": "PayPal", "enabled": True},
            {"id": "crypto", "name": "Cryptocurrency", "enabled": False}
        ]
    }


@router.post("/process-payment")
async def process_payment(
    checkout_data: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Process payment for model purchase(s)
    Integrates with wallet system to track seller earnings
    """
    earnings_service = EarningsService(session)
    transaction_repo = TransactionRepository(session)
    
    # Get models being purchased
    result = await session.execute(
        select(Model).where(Model.id.in_(checkout_data.model_ids))
    )
    models = result.scalars().all()
    
    if len(models) != len(checkout_data.model_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more models not found"
        )
    
    # Check if user already owns any of these models
    for model in models:
        existing_purchase = await transaction_repo.get_purchase(current_user.id, model.id)
        if existing_purchase:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You already own model: {model.title}"
            )
    
    # Calculate total
    total_amount = sum(Decimal(str(model.price)) for model in models)
    
    # TODO: Integrate with actual payment processor (Stripe, PayPal, etc.)
    # For now, simulate successful payment
    payment_successful = True
    stripe_payment_id = f"pi_{uuid4().hex[:24]}"  # Simulated Stripe payment ID
    
    if not payment_successful:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Payment failed"
        )
    
    # Process each model purchase
    transactions = []
    purchases = []
    
    for model in models:
        # Record sale in both transaction table and wallet system
        transaction = await earnings_service.record_model_sale(
            buyer_id=current_user.id,
            seller_id=model.creator_id,
            model_id=model.id,
            amount=Decimal(str(model.price)),
            payment_method=checkout_data.payment_method,
            transaction_id=f"{stripe_payment_id}_{model.id}",
            model_title=model.title
        )
        transactions.append(transaction)
        
        # Create purchase record
        purchase = await transaction_repo.create_purchase(
            user_id=current_user.id,
            model_id=model.id,
            transaction_id=transaction.id
        )
        purchases.append(purchase)
    
    # Clear cart
    for model_id in checkout_data.model_ids:
        await transaction_repo.remove_from_cart(current_user.id, model_id)
    
    # Send purchase confirmation to buyer
    try:
        from app.utils.email import send_purchase_confirmation_email
        from app.core.config import settings
        
        items_list = []
        for model in models:
            # Get creator username
            creator_result = await session.execute(
                select(User).where(User.id == model.creator_id)
            )
            creator = creator_result.scalar_one_or_none()
            
            items_list.append({
                "title": model.title,
                "creator": creator.username if creator else "Unknown",
                "price": float(model.price)
            })
        
        await send_purchase_confirmation_email(
            user_email=current_user.email,
            username=current_user.username,
            transaction_id=stripe_payment_id,
            items=items_list,
            total=float(total_amount),
            download_url=f"{settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'}/downloads/{stripe_payment_id}"
        )
    except Exception as e:
        print(f"Failed to send purchase confirmation: {e}")
    
    # Send sale notification to each creator
    for model in models:
        try:
            from app.utils.email import send_new_sale_email
            from app.core.config import settings
            
            creator_result = await session.execute(
                select(User).where(User.id == model.creator_id)
            )
            creator = creator_result.scalar_one_or_none()
            
            if creator:
                platform_fee = float(model.price) * 0.075  # 7.5%
                earnings = float(model.price) - platform_fee
                
                await send_new_sale_email(
                    user_email=creator.email,
                    username=creator.username,
                    model_title=model.title,
                    sale_price=float(model.price),
                    platform_fee=platform_fee,
                    your_earnings=earnings,
                    transaction_id=stripe_payment_id,
                    dashboard_url=f"{settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'}/dashboard"
                )
        except Exception as e:
            print(f"Failed to send sale notification: {e}")
    
    return {
        "success": True,
        "transaction_id": stripe_payment_id,
        "total_amount": float(total_amount),
        "purchases": [
            {
                "model_id": str(p.model_id),
                "transaction_id": str(p.transaction_id)
            }
            for p in purchases
        ],
        "redirect_url": f"/purchase/success?transaction_id={stripe_payment_id}"
    }
