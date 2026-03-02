from typing import Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.repositories.wallet_repository import WalletRepository
from app.repositories.transaction_repository import TransactionRepository
from app.models.transaction import Transaction


class EarningsService:
    """Service to handle earnings from both model sales and bounties"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.wallet_repo = WalletRepository(db)
        self.transaction_repo = TransactionRepository(db)
    
    async def record_model_sale(
        self,
        buyer_id: UUID,
        seller_id: UUID,
        model_id: UUID,
        amount: Decimal,
        payment_method: str,
        transaction_id: str,
        model_title: Optional[str] = None
    ) -> Transaction:
        """
        Record a model sale in both the transaction table and wallet system
        This ensures earnings are tracked consistently across both systems
        """
        # Calculate platform fee (7.5%)
        platform_fee = amount * Decimal("0.075")
        seller_amount = amount - platform_fee
        
        # 1. Create transaction record (for compatibility with existing system)
        transaction = await self.transaction_repo.create_transaction(
            buyer_id=buyer_id,
            seller_id=seller_id,
            model_id=model_id,
            amount=float(amount),
            platform_fee=float(platform_fee),
            seller_amount=float(seller_amount),
            payment_method=payment_method,
            payment_status='completed',
            transaction_id=transaction_id,
            completed_at=datetime.utcnow()
        )
        
        # 2. Update seller's wallet (new integrated system)
        description = f"Model sale: {model_title}" if model_title else f"Model sale (Transaction: {transaction_id})"
        
        await self.wallet_repo.add_funds(
            user_id=seller_id,
            amount=seller_amount,
            transaction_type='model_sale',
            description=description,
            reference_type='model',
            reference_id=model_id
        )
        
        return transaction
    
    async def get_user_earnings_summary(self, user_id: UUID) -> dict:
        """Get comprehensive earnings summary for a user"""
        wallet = await self.wallet_repo.get_or_create_wallet(user_id)
        
        # Get wallet transactions breakdown
        # Note: get_transactions returns tuple (transactions, total)
        transactions, _ = await self.wallet_repo.get_transactions(
            user_id=user_id,
            limit=1000  # Get all for summary
        )
        
        # Calculate earnings by type
        model_earnings = Decimal("0")
        bounty_earnings = Decimal("0")
        
        for tx in transactions:
            if tx.transaction_type == 'model_sale':
                model_earnings += tx.amount
            elif tx.transaction_type in ['bounty_payment', 'milestone_payment']:
                bounty_earnings += tx.amount
        
        return {
            "total_earned": wallet.total_earned,
            "available_balance": wallet.available_balance,
            "held_balance": wallet.held_balance,
            "model_earnings": model_earnings,
            "bounty_earnings": bounty_earnings,
            "total_deposited": wallet.total_deposited,
            "total_withdrawn": wallet.total_withdrawn,
            "currency": wallet.currency
        }
    
    async def verify_earnings_consistency(self, user_id: UUID) -> dict:
        """
        Verify that wallet earnings match transaction records
        Useful for debugging and ensuring data integrity
        """
        wallet = await self.wallet_repo.get_or_create_wallet(user_id)
        
        # Get all completed transactions for this seller
        from sqlalchemy import select, func
        from app.models.transaction import Transaction
        
        result = await self.db.execute(
            select(func.sum(Transaction.seller_amount))
            .where(Transaction.seller_id == user_id)
            .where(Transaction.payment_status == 'completed')
        )
        transaction_total = result.scalar() or 0
        
        # Get wallet transaction total
        # Note: get_transactions returns tuple (transactions, total)
        wallet_txs, _ = await self.wallet_repo.get_transactions(
            user_id=user_id,
            limit=10000
        )
        
        # Filter for earnings transactions and sum them
        wallet_total = sum(
            tx.amount for tx in wallet_txs 
            if tx.amount > 0 and tx.transaction_type in ['model_sale', 'bounty_payment', 'milestone_payment']
        )
        
        difference = abs(wallet.total_earned - wallet_total)
        is_consistent = difference < Decimal("0.01")  # Allow for rounding
        
        return {
            "wallet_total_earned": wallet.total_earned,
            "wallet_transactions_sum": wallet_total,
            "old_transactions_sum": Decimal(str(transaction_total)),
            "difference": difference,
            "is_consistent": is_consistent,
            "status": "✅ Consistent" if is_consistent else "⚠️ Inconsistent"
        }
