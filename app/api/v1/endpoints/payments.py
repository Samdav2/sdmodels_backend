"""
Payment endpoints for deposits and withdrawals (Paystack + NOWPayments)
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.services.payment_service import PaymentService
from app.services.paystack_service import paystack_service
from app.services.nowpayments_service import nowpayments_service
from app.schemas.payment import (
    DepositRequest,
    DepositResponse,
    WithdrawalRequestCreate,
    WithdrawalRequestResponse,
    AvailableCurrenciesResponse,
    PaymentStatusResponse
)

router = APIRouter()


@router.post("/deposit", response_model=DepositResponse)
async def create_deposit(
    deposit_data: DepositRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a deposit (Paystack for fiat or NOWPayments for crypto)
    
    - **amount**: Amount to deposit
    - **payment_method**: "paystack" or "crypto"
    - **currency**: "NGN" for Paystack, "BTC"/"ETH"/"USDT" etc for crypto
    - **callback_url**: Optional callback URL after payment
    """
    payment_service = PaymentService(db)
    return await payment_service.create_deposit(current_user, deposit_data)


@router.post("/withdraw", response_model=WithdrawalRequestResponse)
async def create_withdrawal(
    withdrawal_data: WithdrawalRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a withdrawal request
    
    For Paystack (fiat):
    - **withdrawal_method**: "paystack"
    - **bank_code**: Bank code
    - **account_number**: Account number
    - **account_name**: Account name
    
    For Crypto:
    - **withdrawal_method**: "crypto"
    - **crypto_address**: Wallet address
    - **crypto_currency**: Currency code (BTC, ETH, USDT, etc)
    - **crypto_extra_id**: Optional extra ID (for XRP, XLM, etc)
    """
    payment_service = PaymentService(db)
    return await payment_service.create_withdrawal(current_user, withdrawal_data)


@router.get("/currencies", response_model=AvailableCurrenciesResponse)
async def get_available_currencies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get available currencies for deposits and withdrawals"""
    payment_service = PaymentService(db)
    return await payment_service.get_available_currencies()


@router.get("/banks")
async def get_banks(
    country: str = "nigeria",
    current_user: User = Depends(get_current_user)
):
    """Get list of banks for Paystack withdrawals"""
    return await paystack_service.list_banks(country)


@router.post("/paystack/verify/{reference}")
async def verify_paystack_payment(
    reference: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Verify Paystack payment and credit wallet"""
    payment_service = PaymentService(db)
    return await payment_service.verify_paystack_payment(reference)


@router.post("/paystack/webhook")
async def paystack_webhook(
    request: Request,
    x_paystack_signature: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Handle Paystack webhook"""
    body = await request.body()
    
    if not x_paystack_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing signature"
        )
    
    return await paystack_service.handle_webhook(
        session=db,
        request_body=body,
        signature=x_paystack_signature
    )


@router.post("/crypto/webhook")
async def crypto_webhook(
    request: Request,
    x_nowpayments_sig: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Handle NOWPayments IPN webhook"""
    body = await request.body()
    payload = await request.json()
    
    if not x_nowpayments_sig:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing signature"
        )
    
    payment_service = PaymentService(db)
    return await payment_service.process_crypto_webhook(payload, x_nowpayments_sig)


@router.get("/crypto/status/{payment_id}")
async def get_crypto_payment_status(
    payment_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get crypto payment status from NOWPayments"""
    return await nowpayments_service.get_payment_status(payment_id)


@router.get("/crypto/estimate")
async def get_crypto_estimate(
    amount: float,
    currency_from: str,
    currency_to: str,
    current_user: User = Depends(get_current_user)
):
    """Get estimated crypto price"""
    return await nowpayments_service.get_estimated_price(
        amount=amount,
        currency_from=currency_from,
        currency_to=currency_to
    )


@router.get("/crypto/minimum")
async def get_crypto_minimum(
    currency_from: str,
    currency_to: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get minimum crypto amount"""
    return await nowpayments_service.get_minimum_amount(
        currency_from=currency_from,
        currency_to=currency_to
    )


@router.post("/crypto/validate-address")
async def validate_crypto_address(
    address: str,
    currency: str,
    extra_id: str = None,
    current_user: User = Depends(get_current_user)
):
    """Validate a crypto address"""
    is_valid = await nowpayments_service.validate_address(
        address=address,
        currency=currency,
        extra_id=extra_id
    )
    
    return {
        "valid": is_valid,
        "address": address,
        "currency": currency
    }


@router.get("/paystack/resolve-account")
async def resolve_account(
    account_number: str,
    bank_code: str,
    current_user: User = Depends(get_current_user)
):
    """Resolve bank account number to get account name"""
    return await paystack_service.resolve_account_number(
        account_number=account_number,
        bank_code=bank_code
    )
