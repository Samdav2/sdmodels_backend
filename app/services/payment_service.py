"""
Unified payment service integrating Paystack and NOWPayments with wallet system
"""
from typing import Optional, List, Tuple
from uuid import UUID
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.paystack_service import paystack_service
from app.services.nowpayments_service import nowpayments_service
from app.services.wallet_service import WalletService
from app.core.config import settings
from app.schemas.payment import (
    DepositRequest,
    DepositResponse,
    WithdrawalRequestCreate,
    WithdrawalRequestResponse,
    AvailableCurrenciesResponse,
    AvailableCurrency,
    PaystackRecipientRequest,
    NOWPaymentsInvoiceRequest,
    NOWPaymentsPaymentRequest
)
from app.models.payment import WithdrawalRequest as WithdrawalRequestModel
from app.models.user import User


class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.wallet_service = WalletService(db)
    
    async def create_deposit(
        self,
        user: User,
        deposit_data: DepositRequest
    ) -> DepositResponse:
        """Create a deposit (Paystack or Crypto)"""
        # Validate minimum amount
        if deposit_data.amount < Decimal(str(settings.MIN_DEPOSIT_AMOUNT)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Minimum deposit amount is {settings.MIN_DEPOSIT_AMOUNT}"
            )
        
        # Get or create wallet
        wallet = await self.wallet_service.get_wallet(user.id)
        
        if deposit_data.payment_method == "paystack":
            # Paystack deposit
            result = await paystack_service.initialize_transaction(
                session=self.db,
                user_id=user.id,
                wallet_id=wallet.id,
                email=user.email,
                amount=deposit_data.amount,
                callback_url=deposit_data.callback_url
            )
            
            return DepositResponse(
                payment_id=UUID(str(wallet.id)),  # Temporary, will be updated
                amount=deposit_data.amount,
                currency=deposit_data.currency,
                payment_method="paystack",
                status="pending",
                authorization_url=result.authorization_url,
                reference=result.reference
            )
        
        elif deposit_data.payment_method == "crypto":
            # Crypto deposit via NOWPayments
            order_id = f"deposit_{user.id}_{int(deposit_data.amount * 100)}"
            
            # Create invoice
            invoice_request = NOWPaymentsInvoiceRequest(
                price_amount=deposit_data.amount,
                price_currency=deposit_data.currency,
                pay_currency=deposit_data.currency,
                order_id=order_id,
                order_description=f"Wallet deposit - {deposit_data.amount} {deposit_data.currency}",
                ipn_callback_url=f"{settings.API_V1_STR}/payments/crypto/webhook",
                is_fee_paid_by_user=False
            )
            
            payment = await nowpayments_service.create_invoice(
                session=self.db,
                invoice_data=invoice_request,
                user_id=user.id,
                wallet_id=wallet.id
            )
            
            return DepositResponse(
                payment_id=payment.id,
                amount=deposit_data.amount,
                currency=deposit_data.currency,
                payment_method="crypto",
                status="waiting",
                invoice_url=payment.invoice_url,
                pay_address=payment.pay_address,
                pay_amount=payment.pay_amount,
                pay_currency=payment.pay_currency
            )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payment method. Use 'paystack' or 'crypto'"
            )
    
    async def create_withdrawal(
        self,
        user: User,
        withdrawal_data: WithdrawalRequestCreate
    ) -> WithdrawalRequestResponse:
        """Create a withdrawal request"""
        # Validate minimum amount
        if withdrawal_data.amount < Decimal(str(settings.MIN_WITHDRAWAL_AMOUNT)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Minimum withdrawal amount is {settings.MIN_WITHDRAWAL_AMOUNT}"
            )
        
        # Check balance
        wallet = await self.wallet_service.get_wallet(user.id)
        if wallet.available_balance < withdrawal_data.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient balance. Available: {wallet.available_balance}"
            )
        
        # Create withdrawal request
        withdrawal_request = WithdrawalRequestModel(
            user_id=user.id,
            wallet_id=wallet.id,
            amount=withdrawal_data.amount,
            currency="NGN" if withdrawal_data.withdrawal_method == "paystack" else withdrawal_data.crypto_currency,
            withdrawal_method=withdrawal_data.withdrawal_method,
            status="pending"
        )
        
        if withdrawal_data.withdrawal_method == "paystack":
            # Paystack withdrawal
            if not all([withdrawal_data.bank_code, withdrawal_data.account_number, withdrawal_data.account_name]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bank details required for Paystack withdrawal"
                )
            
            # Resolve account to verify
            try:
                account_info = await paystack_service.resolve_account_number(
                    account_number=withdrawal_data.account_number,
                    bank_code=withdrawal_data.bank_code
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid bank account: {str(e)}"
                )
            
            withdrawal_request.bank_code = withdrawal_data.bank_code
            withdrawal_request.account_number = withdrawal_data.account_number
            withdrawal_request.account_name = account_info.get("account_name")
            
            # Deduct from wallet immediately
            await self.wallet_service.wallet_repo.withdraw(
                user_id=user.id,
                amount=withdrawal_data.amount,
                withdrawal_method="paystack",
                bank_account_id=withdrawal_data.account_number
            )
            
            withdrawal_request.status = "processing"
        
        elif withdrawal_data.withdrawal_method == "crypto":
            # Crypto withdrawal
            if not all([withdrawal_data.crypto_address, withdrawal_data.crypto_currency]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Crypto address and currency required for crypto withdrawal"
                )
            
            # Validate address
            is_valid = await nowpayments_service.validate_address(
                address=withdrawal_data.crypto_address,
                currency=withdrawal_data.crypto_currency,
                extra_id=withdrawal_data.crypto_extra_id
            )
            
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid crypto address"
                )
            
            withdrawal_request.crypto_address = withdrawal_data.crypto_address
            withdrawal_request.crypto_currency = withdrawal_data.crypto_currency
            withdrawal_request.crypto_extra_id = withdrawal_data.crypto_extra_id
            
            # Deduct from wallet immediately
            await self.wallet_service.wallet_repo.withdraw(
                user_id=user.id,
                amount=withdrawal_data.amount,
                withdrawal_method="crypto",
                bank_account_id=withdrawal_data.crypto_address
            )
            
            withdrawal_request.status = "processing"
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid withdrawal method. Use 'paystack' or 'crypto'"
            )
        
        self.db.add(withdrawal_request)
        await self.db.commit()
        await self.db.refresh(withdrawal_request)
        
        return WithdrawalRequestResponse(
            id=withdrawal_request.id,
            user_id=withdrawal_request.user_id,
            amount=withdrawal_request.amount,
            currency=withdrawal_request.currency,
            withdrawal_method=withdrawal_request.withdrawal_method,
            status=withdrawal_request.status,
            created_at=withdrawal_request.created_at,
            bank_code=withdrawal_request.bank_code,
            account_number=withdrawal_request.account_number,
            account_name=withdrawal_request.account_name,
            crypto_address=withdrawal_request.crypto_address,
            crypto_currency=withdrawal_request.crypto_currency
        )
    
    async def get_available_currencies(self) -> AvailableCurrenciesResponse:
        """Get available currencies for deposits/withdrawals"""
        # Fiat currencies (Paystack)
        fiat = [
            AvailableCurrency(
                code="NGN",
                name="Nigerian Naira",
                is_popular=True
            )
        ]
        
        # Crypto currencies (NOWPayments)
        try:
            crypto_list = await nowpayments_service.get_available_currencies()
            crypto = []
            
            popular_cryptos = ["BTC", "ETH", "USDT", "USDC", "BNB", "TRX"]
            
            for currency in crypto_list:
                code = currency.get("code", "").upper()
                crypto.append(AvailableCurrency(
                    code=code,
                    name=currency.get("name", code),
                    network=currency.get("network"),
                    is_popular=code in popular_cryptos
                ))
        except:
            # Fallback if API fails
            crypto = [
                AvailableCurrency(code="BTC", name="Bitcoin", is_popular=True),
                AvailableCurrency(code="ETH", name="Ethereum", is_popular=True),
                AvailableCurrency(code="USDT", name="Tether", is_popular=True),
                AvailableCurrency(code="USDC", name="USD Coin", is_popular=True),
            ]
        
        return AvailableCurrenciesResponse(fiat=fiat, crypto=crypto)
    
    async def get_banks(self, country: str = "nigeria") -> List[dict]:
        """Get list of banks for Paystack"""
        return await paystack_service.list_banks(country)
    
    async def verify_paystack_payment(self, reference: str):
        """Verify Paystack payment and credit wallet"""
        result = await paystack_service.verify_transaction(self.db, reference)
        
        if result.status == "success":
            # Credit wallet
            from sqlalchemy import select
            from app.models.payment import Payment
            
            statement = select(Payment).where(Payment.reference == reference)
            payment_result = await self.db.execute(statement)
            payment = payment_result.scalar_one_or_none()
            
            if payment and payment.status == "success":
                # Deposit to wallet
                await self.wallet_service.wallet_repo.deposit(
                    user_id=payment.user_id,
                    amount=payment.amount,
                    payment_method="paystack",
                    payment_intent_id=reference
                )
        
        return result
    
    async def process_crypto_webhook(self, payload: dict, signature: str):
        """Process NOWPayments webhook and credit wallet"""
        from app.schemas.payment import NOWPaymentsIPNPayload
        
        ipn_payload = NOWPaymentsIPNPayload(**payload)
        payment = await nowpayments_service.process_ipn_callback(
            session=self.db,
            payload=ipn_payload,
            signature=signature
        )
        
        if payment and payment.payment_status == "finished":
            # Credit wallet
            await self.wallet_service.wallet_repo.deposit(
                user_id=payment.user_id,
                amount=payment.price_amount,
                payment_method="crypto",
                payment_intent_id=str(payment.payment_id)
            )
        
        return payment
