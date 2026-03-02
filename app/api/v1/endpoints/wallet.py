from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.services.wallet_service import WalletService
from app.services.paystack_service import paystack_service
from app.schemas.wallet import (
    WalletResponse, WalletBalanceResponse,
    DepositRequest, DepositResponse,
    WithdrawalRequest, WithdrawalResponse,
    TransactionListResponse
)

router = APIRouter()


@router.get("/balance", response_model=WalletBalanceResponse)
async def get_wallet_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's wallet balance
    
    Returns:
    - available_balance: Funds available for use
    - held_balance: Funds held in escrow
    - total_balance: Sum of available and held
    - Statistics: total deposited, withdrawn, earned
    """
    wallet_service = WalletService(db)
    return await wallet_service.get_balance(current_user.id)


@router.get("/", response_model=WalletResponse)
async def get_wallet(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's complete wallet information
    """
    wallet_service = WalletService(db)
    return await wallet_service.get_wallet(current_user.id)


@router.post("/deposit", response_model=DepositResponse)
async def deposit_funds(
    deposit_data: DepositRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Initialize a deposit transaction
    
    Parameters:
    - amount: Amount to deposit (must be positive)
    - payment_method: Payment method (paystack, crypto)
    - callback_url: URL to redirect after payment (optional)
    
    Returns:
    - transaction_id: Transaction reference
    - authorization_url: Paystack payment URL (for paystack method)
    - access_code: Paystack access code (for paystack method)
    - status: Transaction status (pending)
    
    Note: Transaction is created with 'pending' status.
    Use webhook or verify endpoint to confirm payment.
    """
    wallet_service = WalletService(db)
    
    if deposit_data.payment_method == "paystack":
        return await wallet_service.initialize_paystack_deposit(
            user_id=current_user.id,
            email=current_user.email,
            amount=deposit_data.amount,
            callback_url=deposit_data.callback_url
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment method '{deposit_data.payment_method}' not supported"
        )


@router.post("/withdraw", response_model=WithdrawalResponse)
async def withdraw_funds(
    withdrawal_data: WithdrawalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Withdraw funds from wallet
    
    Parameters:
    - amount: Amount to withdraw (must be positive and <= available balance)
    - withdrawal_method: Withdrawal method (bank_transfer, paypal, etc.)
    - bank_account_id: Bank account ID (optional)
    
    Note: Withdrawals are marked as pending and require manual processing.
    In production, integrate with payment gateway for automatic transfers.
    """
    wallet_service = WalletService(db)
    return await wallet_service.withdraw(current_user.id, withdrawal_data)


@router.get("/transactions", response_model=TransactionListResponse)
async def get_transactions(
    transaction_type: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get transaction history
    
    Query Parameters:
    - transaction_type: Filter by type (deposit, withdrawal, bounty_escrow, bounty_payment, etc.)
    - status: Filter by status (pending, completed, failed, cancelled)
    - page: Page number (default: 1)
    - limit: Items per page (default: 20, max: 100)
    
    Transaction Types:
    - deposit: Funds added to wallet
    - withdrawal: Funds removed from wallet
    - bounty_escrow: Funds held for bounty
    - bounty_payment: Payment to artist
    - bounty_refund: Refund from cancelled bounty
    - model_purchase: Purchase of 3D model
    - model_sale: Earnings from model sale
    - platform_fee: Platform commission
    - milestone_escrow: Funds held for milestone
    - milestone_payment: Payment for completed milestone
    """
    if limit > 100:
        limit = 100
    
    wallet_service = WalletService(db)
    return await wallet_service.get_transactions(
        user_id=current_user.id,
        transaction_type=transaction_type,
        status=status,
        page=page,
        limit=limit
    )


@router.get("/earnings/summary")
async def get_earnings_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive earnings summary
    
    Returns breakdown of:
    - Total earned (all sources)
    - Model sales earnings
    - Bounty earnings
    - Available balance
    - Held balance (in escrow)
    """
    from app.services.earnings_service import EarningsService
    
    earnings_service = EarningsService(db)
    return await earnings_service.get_user_earnings_summary(current_user.id)


@router.get("/earnings/verify")
async def verify_earnings_consistency(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Verify earnings consistency between wallet and transaction records
    Useful for debugging and ensuring data integrity
    """
    from app.services.earnings_service import EarningsService
    
    earnings_service = EarningsService(db)
    return await earnings_service.verify_earnings_consistency(current_user.id)


@router.get("/verify/{reference}")
async def verify_payment(
    reference: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify a payment transaction (PUBLIC ENDPOINT)
    
    Parameters:
    - reference: Transaction reference from Paystack
    
    Returns:
    - status: Payment status (success, failed, pending)
    - transaction: Transaction details
    - wallet_balance: Updated wallet balance
    
    This endpoint is called after Paystack redirects the user back.
    It does not require authentication because Paystack callbacks
    don't include auth tokens. The payment is verified using
    Paystack's API and the user_id is retrieved from the payment record.
    """
    wallet_service = WalletService(db)
    return await wallet_service.verify_paystack_payment_public(reference=reference)


@router.post("/paystack/webhook")
async def paystack_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Paystack webhook handler
    
    This endpoint receives payment notifications from Paystack.
    It verifies the signature and updates transaction status.
    
    Configure this URL in Paystack Dashboard:
    https://yourdomain.com/api/v1/wallet/paystack/webhook
    
    Events handled:
    - charge.success: Payment successful
    - transfer.success: Withdrawal successful
    - transfer.failed: Withdrawal failed
    """
    # Get signature from headers
    signature = request.headers.get("x-paystack-signature")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing signature"
        )
    
    # Get request body
    body = await request.body()
    
    # Handle webhook
    wallet_service = WalletService(db)
    return await wallet_service.handle_paystack_webhook(body, signature)
