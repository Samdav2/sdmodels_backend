from typing import Optional, List, Tuple
from uuid import UUID
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.wallet_repository import WalletRepository
from app.services.paystack_service import paystack_service
from app.models.payment import Payment
from app.schemas.wallet import (
    WalletResponse, WalletBalanceResponse,
    DepositRequest, DepositResponse,
    WithdrawalRequest, WithdrawalResponse,
    TransactionResponse, TransactionListResponse
)
from app.models.wallet import Wallet, WalletTransaction
import json


class WalletService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.wallet_repo = WalletRepository(db)
    
    async def get_wallet(self, user_id: UUID) -> WalletResponse:
        """Get or create user's wallet"""
        wallet = await self.wallet_repo.get_or_create_wallet(user_id)
        
        return WalletResponse(
            id=wallet.id,
            user_id=wallet.user_id,
            available_balance=wallet.available_balance,
            held_balance=wallet.held_balance,
            total_balance=wallet.available_balance + wallet.held_balance,
            total_deposited=wallet.total_deposited,
            total_withdrawn=wallet.total_withdrawn,
            total_earned=wallet.total_earned,
            currency=wallet.currency,
            created_at=wallet.created_at,
            updated_at=wallet.updated_at
        )
    
    async def get_balance(self, user_id: UUID) -> WalletBalanceResponse:
        """Get user's wallet balance"""
        wallet = await self.wallet_repo.get_or_create_wallet(user_id)
        
        return WalletBalanceResponse(
            wallet_id=wallet.id,
            available_balance=wallet.available_balance,
            held_balance=wallet.held_balance,
            total_balance=wallet.available_balance + wallet.held_balance,
            currency=wallet.currency,
            total_deposited=wallet.total_deposited,
            total_withdrawn=wallet.total_withdrawn,
            total_earned=wallet.total_earned
        )
    
    async def deposit(self, user_id: UUID, deposit_data: DepositRequest) -> DepositResponse:
        """Deposit funds to wallet"""
        # TODO: Integrate with payment gateway (Stripe/PayPal)
        # For now, we'll simulate successful payment
        
        wallet, transaction = await self.wallet_repo.deposit(
            user_id=user_id,
            amount=deposit_data.amount,
            payment_method=deposit_data.payment_method,
            payment_intent_id=deposit_data.payment_intent_id
        )
        
        return DepositResponse(
            transaction_id=transaction.id,
            amount=deposit_data.amount,
            new_balance=wallet.available_balance,
            status="completed"
        )
    
    async def withdraw(self, user_id: UUID, withdrawal_data: WithdrawalRequest) -> WithdrawalResponse:
        """Withdraw funds from wallet"""
        # Check if user has sufficient balance
        wallet = await self.wallet_repo.get_or_create_wallet(user_id)
        
        if wallet.available_balance < withdrawal_data.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient balance. Available: ${wallet.available_balance}, Required: ${withdrawal_data.amount}"
            )
        
        # TODO: Integrate with payment gateway for actual withdrawal
        # For now, we'll mark as pending
        
        wallet, transaction = await self.wallet_repo.withdraw(
            user_id=user_id,
            amount=withdrawal_data.amount,
            withdrawal_method=withdrawal_data.withdrawal_method,
            bank_account_id=withdrawal_data.bank_account_id
        )
        
        # Send withdrawal email
        try:
            from app.utils.email import send_wallet_withdrawal_email
            from app.core.config import settings
            from datetime import datetime
            from sqlalchemy import select
            from app.models.user import User
            
            user_result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if user:
                await send_wallet_withdrawal_email(
                    user_email=user.email,
                    username=user.username,
                    amount=float(withdrawal_data.amount),
                    transaction_id=str(transaction.id),
                    withdrawal_method=withdrawal_data.withdrawal_method,
                    transaction_date=datetime.now().strftime("%Y-%m-%d %H:%M %p"),
                    remaining_balance=float(wallet.available_balance)
                )
        except Exception as e:
            print(f"Failed to send withdrawal email: {e}")
        
        return WithdrawalResponse(
            transaction_id=transaction.id,
            amount=withdrawal_data.amount,
            new_balance=wallet.available_balance,
            status="pending",
            estimated_arrival="3-5 business days"
        )
    
    async def get_transactions(
        self,
        user_id: UUID,
        transaction_type: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> TransactionListResponse:
        """Get user's transaction history"""
        skip = (page - 1) * limit
        
        transactions, total = await self.wallet_repo.get_transactions(
            user_id=user_id,
            transaction_type=transaction_type,
            status=status,
            skip=skip,
            limit=limit
        )
        
        transaction_responses = []
        for tx in transactions:
            # Parse transaction_metadata if it's a string
            tx_metadata = tx.transaction_metadata
            if isinstance(tx_metadata, str):
                import json
                tx_metadata = json.loads(tx_metadata)
            
            transaction_responses.append(
                TransactionResponse(
                    id=tx.id,
                    wallet_id=tx.wallet_id,
                    user_id=tx.user_id,
                    transaction_type=tx.transaction_type,
                    amount=tx.amount,
                    balance_before=tx.balance_before,
                    balance_after=tx.balance_after,
                    status=tx.status,
                    description=tx.description,
                    reference_type=tx.reference_type,
                    reference_id=tx.reference_id,
                    transaction_metadata=tx_metadata,
                    created_at=tx.created_at
                )
            )
        
        return TransactionListResponse(
            transactions=transaction_responses,
            total=total,
            page=page,
            limit=limit
        )
    
    async def check_sufficient_balance(self, user_id: UUID, required_amount: Decimal) -> bool:
        """Check if user has sufficient balance"""
        wallet = await self.wallet_repo.get_or_create_wallet(user_id)
        return wallet.available_balance >= required_amount
    
    async def hold_funds_for_bounty(
        self,
        user_id: UUID,
        amount: Decimal,
        bounty_id: UUID,
        description: str
    ) -> Tuple[Wallet, WalletTransaction]:
        """Hold funds in escrow for bounty"""
        return await self.wallet_repo.hold_funds(
            user_id=user_id,
            amount=amount,
            description=description,
            reference_type="bounty",
            reference_id=bounty_id
        )
    
    async def release_bounty_payment(
        self,
        from_user_id: UUID,
        to_user_id: UUID,
        amount: Decimal,
        bounty_id: UUID,
        description: str
    ) -> Tuple[Wallet, Wallet, List[WalletTransaction]]:
        """Release bounty payment to artist"""
        # Calculate platform fee (7.5%)
        platform_fee = amount * Decimal("0.075")
        
        return await self.wallet_repo.release_funds(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            amount=amount,
            platform_fee=platform_fee,
            description=description,
            reference_type="bounty",
            reference_id=bounty_id
        )
    
    async def refund_bounty(
        self,
        user_id: UUID,
        amount: Decimal,
        bounty_id: UUID,
        description: str
    ) -> Tuple[Wallet, WalletTransaction]:
        """Refund bounty to client"""
        return await self.wallet_repo.refund_held_funds(
            user_id=user_id,
            amount=amount,
            description=description,
            reference_type="bounty",
            reference_id=bounty_id
        )
    
    async def initialize_paystack_deposit(
        self,
        user_id: UUID,
        email: str,
        amount: Decimal,
        callback_url: Optional[str] = None
    ) -> DepositResponse:
        """Initialize Paystack deposit transaction"""
        # Get or create wallet
        wallet = await self.wallet_repo.get_or_create_wallet(user_id)
        
        # Initialize Paystack transaction
        response = await paystack_service.initialize_transaction(
            session=self.db,
            user_id=user_id,
            wallet_id=wallet.id,
            email=email,
            amount=amount,
            callback_url=callback_url
        )
        
        # Get the payment record to get transaction_id
        statement = select(Payment).where(Payment.reference == response.reference)
        result = await self.db.execute(statement)
        payment = result.scalar_one_or_none()
        
        return DepositResponse(
            transaction_id=payment.id if payment else None,
            reference=response.reference,
            amount=amount,
            authorization_url=response.authorization_url,
            access_code=response.access_code,
            new_balance=wallet.available_balance,
            status="pending"
        )
    
    async def verify_paystack_payment(
        self,
        user_id: UUID,
        reference: str
    ) -> dict:
        """Verify Paystack payment and update wallet"""
        # Verify with Paystack
        verify_response = await paystack_service.verify_transaction(
            session=self.db,
            reference=reference
        )
        
        if verify_response.status != "success":
            return {
                "status": "failed",
                "message": "Payment verification failed",
                "data": verify_response.data
            }
        
        # Get payment record
        statement = select(Payment).where(Payment.reference == reference)
        result = await self.db.execute(statement)
        payment = result.scalar_one_or_none()
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        
        # Verify user owns this payment
        if payment.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this payment"
            )
        
        # Check if already processed
        if payment.status == "success":
            # Get current wallet balance
            wallet = await self.wallet_repo.get_or_create_wallet(user_id)
            return {
                "status": "success",
                "message": "Payment already processed",
                "transaction": {
                    "id": str(payment.id),
                    "reference": payment.reference,
                    "amount": float(payment.amount),
                    "status": payment.status
                },
                "wallet_balance": {
                    "available_balance": float(wallet.available_balance),
                    "total_balance": float(wallet.available_balance + wallet.held_balance)
                }
            }
        
        # Update wallet balance
        wallet, transaction = await self.wallet_repo.deposit(
            user_id=user_id,
            amount=payment.amount,
            payment_method="paystack",
            payment_intent_id=reference
        )
        
        # Send deposit confirmation email
        try:
            from app.utils.email import send_wallet_deposit_email
            from app.core.config import settings
            from datetime import datetime
            from sqlalchemy import select
            from app.models.user import User
            
            user_result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if user:
                await send_wallet_deposit_email(
                    user_email=user.email,
                    username=user.username,
                    amount=float(payment.amount),
                    transaction_id=reference,
                    payment_method="Paystack",
                    transaction_date=datetime.now().strftime("%Y-%m-%d %H:%M %p"),
                    new_balance=float(wallet.available_balance),
                    wallet_url=f"{settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'}/wallet"
                )
        except Exception as e:
            print(f"Failed to send deposit email: {e}")
        
        return {
            "status": "success",
            "message": "Payment verified and wallet updated",
            "transaction": {
                "id": str(transaction.id),
                "reference": payment.reference,
                "amount": float(payment.amount),
                "status": "completed"
            },
            "wallet_balance": {
                "available_balance": float(wallet.available_balance),
                "total_balance": float(wallet.available_balance + wallet.held_balance)
            }
        }
    
    async def verify_paystack_payment_public(self, reference: str) -> dict:
        """
        Verify Paystack payment without authentication (PUBLIC)
        
        This method is used when Paystack redirects users back after payment.
        It retrieves the user_id from the payment record and verifies the payment.
        """
        # Verify with Paystack first
        verify_response = await paystack_service.verify_transaction(
            session=self.db,
            reference=reference
        )
        
        if verify_response.status != "success":
            return {
                "status": "failed",
                "message": "Payment verification failed",
                "data": verify_response.data
            }
        
        # Get payment record
        statement = select(Payment).where(Payment.reference == reference)
        result = await self.db.execute(statement)
        payment = result.scalar_one_or_none()
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        
        # Get user_id from payment record
        user_id = payment.user_id
        
        # Check if wallet transaction already exists for this payment
        # The payment reference is stored in transaction_metadata JSON field
        from app.models.wallet import WalletTransaction
        from sqlalchemy import cast, String
        from sqlalchemy.dialects.postgresql import JSONB
        
        tx_statement = select(WalletTransaction).where(
            WalletTransaction.user_id == user_id,
            WalletTransaction.transaction_type == "deposit",
            cast(WalletTransaction.transaction_metadata, JSONB)["payment_intent_id"].astext == reference
        )
        tx_result = await self.db.execute(tx_statement)
        existing_transaction = tx_result.scalar_one_or_none()
        
        if existing_transaction:
            # Payment already processed and wallet already credited
            wallet = await self.wallet_repo.get_or_create_wallet(user_id)
            return {
                "status": "success",
                "message": "Payment already processed",
                "transaction": {
                    "id": str(existing_transaction.id),
                    "reference": payment.reference,
                    "amount": float(payment.amount),
                    "status": "completed"
                },
                "wallet_balance": {
                    "available_balance": float(wallet.available_balance),
                    "total_balance": float(wallet.available_balance + wallet.held_balance)
                }
            }
        
        # Payment verified but wallet not yet credited - add funds now
        # Convert currency if needed (Paystack uses NGN, wallet uses USD)
        from app.services.currency_service import currency_service
        
        amount_to_deposit = payment.amount
        original_currency = payment.currency
        
        if original_currency != "USD":
            # Convert to USD
            amount_to_deposit = await currency_service.convert(
                amount=payment.amount,
                from_currency=original_currency,
                to_currency="USD"
            )
            print(f"Currency conversion: {payment.amount} {original_currency} = {amount_to_deposit} USD")
        
        wallet, transaction = await self.wallet_repo.deposit(
            user_id=user_id,
            amount=amount_to_deposit,
            payment_method="paystack",
            payment_intent_id=reference
        )
        
        return {
            "status": "success",
            "message": "Payment verified and wallet updated",
            "transaction": {
                "id": str(transaction.id),
                "reference": payment.reference,
                "amount": float(amount_to_deposit),
                "original_amount": float(payment.amount),
                "original_currency": original_currency,
                "wallet_currency": "USD",
                "status": "completed"
            },
            "wallet_balance": {
                "available_balance": float(wallet.available_balance),
                "total_balance": float(wallet.available_balance + wallet.held_balance)
            }
        }
    
    async def handle_paystack_webhook(
        self,
        request_body: bytes,
        signature: str
    ) -> dict:
        """Handle Paystack webhook events"""
        # Verify and process webhook
        result = await paystack_service.handle_webhook(
            session=self.db,
            request_body=request_body,
            signature=signature
        )
        
        # Parse event
        event = json.loads(request_body)
        
        # If charge.success, update wallet
        if event["event"] == "charge.success":
            data = event["data"]
            reference = data["reference"]
            
            # Get payment record
            statement = select(Payment).where(Payment.reference == reference)
            result_query = await self.db.execute(statement)
            payment = result_query.scalar_one_or_none()
            
            if payment and payment.status == "success":
                # Check if wallet already updated
                statement = select(WalletTransaction).where(
                    WalletTransaction.transaction_metadata.contains(f'"payment_reference": "{reference}"')
                )
                tx_result = await self.db.execute(statement)
                existing_tx = tx_result.scalar_one_or_none()
                
                if not existing_tx:
                    # Update wallet balance
                    await self.wallet_repo.deposit(
                        user_id=payment.user_id,
                        amount=payment.amount,
                        payment_method="paystack",
                        payment_intent_id=reference
                    )
        
        return result
