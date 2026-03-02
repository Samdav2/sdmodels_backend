from uuid import UUID
from typing import Optional, List, Tuple
from decimal import Decimal
from datetime import datetime
from sqlmodel import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.wallet import Wallet, WalletTransaction
import json


class WalletRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # Wallet CRUD
    async def create_wallet(self, user_id: UUID) -> Wallet:
        """Create a new wallet for a user"""
        wallet = Wallet(user_id=user_id)
        self.db.add(wallet)
        await self.db.commit()
        await self.db.refresh(wallet)
        return wallet
    
    async def get_wallet_by_user_id(self, user_id: UUID) -> Optional[Wallet]:
        """Get wallet by user ID"""
        query = select(Wallet).where(Wallet.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_or_create_wallet(self, user_id: UUID) -> Wallet:
        """Get existing wallet or create new one"""
        wallet = await self.get_wallet_by_user_id(user_id)
        if not wallet:
            wallet = await self.create_wallet(user_id)
        return wallet
    
    async def update_wallet_balance(
        self,
        wallet_id: UUID,
        available_delta: Decimal = Decimal("0"),
        held_delta: Decimal = Decimal("0")
    ) -> Wallet:
        """Update wallet balances"""
        wallet = await self.db.get(Wallet, wallet_id)
        if not wallet:
            raise ValueError("Wallet not found")
        
        wallet.available_balance += available_delta
        wallet.held_balance += held_delta
        wallet.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(wallet)
        return wallet
    
    # Transaction CRUD
    async def create_transaction(
        self,
        wallet_id: UUID,
        user_id: UUID,
        transaction_type: str,
        amount: Decimal,
        balance_before: Decimal,
        balance_after: Decimal,
        status: str = "completed",
        description: Optional[str] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[UUID] = None,
        transaction_metadata: Optional[dict] = None
    ) -> WalletTransaction:
        """Create a wallet transaction"""
        transaction = WalletTransaction(
            wallet_id=wallet_id,
            user_id=user_id,
            transaction_type=transaction_type,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            status=status,
            description=description,
            reference_type=reference_type,
            reference_id=reference_id,
            transaction_metadata=json.dumps(transaction_metadata or {})
        )
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        return transaction
    
    async def get_transactions(
        self,
        user_id: UUID,
        transaction_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[WalletTransaction], int]:
        """Get user's wallet transactions with filters"""
        query = select(WalletTransaction).where(WalletTransaction.user_id == user_id)
        
        filters = []
        if transaction_type and transaction_type != "all":
            filters.append(WalletTransaction.transaction_type == transaction_type)
        if status:
            filters.append(WalletTransaction.status == status)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Get total count
        count_query = select(func.count()).select_from(WalletTransaction).where(
            WalletTransaction.user_id == user_id
        )
        if filters:
            count_query = count_query.where(and_(*filters))
        
        result = await self.db.execute(count_query)
        total = result.scalar_one()
        
        # Get paginated results
        query = query.order_by(WalletTransaction.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        transactions = result.scalars().all()
        
        return list(transactions), total
    
    async def get_transaction_by_id(self, transaction_id: UUID) -> Optional[WalletTransaction]:
        """Get transaction by ID"""
        return await self.db.get(WalletTransaction, transaction_id)
    
    # Balance operations
    async def deposit(
        self,
        user_id: UUID,
        amount: Decimal,
        payment_method: str,
        payment_intent_id: Optional[str] = None
    ) -> Tuple[Wallet, WalletTransaction]:
        """Deposit funds to wallet"""
        wallet = await self.get_or_create_wallet(user_id)
        
        balance_before = wallet.available_balance
        balance_after = balance_before + amount
        
        # Update wallet
        wallet.available_balance = balance_after
        wallet.total_deposited += amount
        wallet.updated_at = datetime.utcnow()
        
        # Create transaction
        transaction = await self.create_transaction(
            wallet_id=wallet.id,
            user_id=user_id,
            transaction_type="deposit",
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=f"Deposit via {payment_method}",
            transaction_metadata={"payment_method": payment_method, "payment_intent_id": payment_intent_id}
        )
        
        await self.db.commit()
        await self.db.refresh(wallet)
        
        return wallet, transaction
    
    async def withdraw(
        self,
        user_id: UUID,
        amount: Decimal,
        withdrawal_method: str,
        bank_account_id: Optional[str] = None
    ) -> Tuple[Wallet, WalletTransaction]:
        """Withdraw funds from wallet"""
        wallet = await self.get_or_create_wallet(user_id)
        
        if wallet.available_balance < amount:
            raise ValueError(f"Insufficient balance. Available: {wallet.available_balance}, Required: {amount}")
        
        balance_before = wallet.available_balance
        balance_after = balance_before - amount
        
        # Update wallet
        wallet.available_balance = balance_after
        wallet.total_withdrawn += amount
        wallet.updated_at = datetime.utcnow()
        
        # Create transaction
        transaction = await self.create_transaction(
            wallet_id=wallet.id,
            user_id=user_id,
            transaction_type="withdrawal",
            amount=-amount,
            balance_before=balance_before,
            balance_after=balance_after,
            status="pending",
            description=f"Withdrawal via {withdrawal_method}",
            transaction_metadata={"withdrawal_method": withdrawal_method, "bank_account_id": bank_account_id}
        )
        
        await self.db.commit()
        await self.db.refresh(wallet)
        
        return wallet, transaction
    
    async def hold_funds(
        self,
        user_id: UUID,
        amount: Decimal,
        description: str,
        reference_type: str,
        reference_id: UUID
    ) -> Tuple[Wallet, WalletTransaction]:
        """Hold funds in escrow (move from available to held)"""
        wallet = await self.get_or_create_wallet(user_id)
        
        if wallet.available_balance < amount:
            raise ValueError(f"Insufficient balance. Available: {wallet.available_balance}, Required: {amount}")
        
        balance_before = wallet.available_balance
        balance_after = balance_before - amount
        
        # Update wallet
        wallet.available_balance = balance_after
        wallet.held_balance += amount
        wallet.updated_at = datetime.utcnow()
        
        # Create transaction
        transaction = await self.create_transaction(
            wallet_id=wallet.id,
            user_id=user_id,
            transaction_type=f"{reference_type}_escrow",
            amount=-amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description,
            reference_type=reference_type,
            reference_id=reference_id
        )
        
        await self.db.commit()
        await self.db.refresh(wallet)
        
        return wallet, transaction
    
    async def release_funds(
        self,
        from_user_id: UUID,
        to_user_id: UUID,
        amount: Decimal,
        platform_fee: Decimal,
        description: str,
        reference_type: str,
        reference_id: UUID
    ) -> Tuple[Wallet, Wallet, List[WalletTransaction]]:
        """Release held funds to recipient (with platform fee)"""
        from_wallet = await self.get_or_create_wallet(from_user_id)
        to_wallet = await self.get_or_create_wallet(to_user_id)
        
        if from_wallet.held_balance < amount:
            raise ValueError(f"Insufficient held balance. Held: {from_wallet.held_balance}, Required: {amount}")
        
        artist_amount = amount - platform_fee
        
        # Update from_wallet (remove from held)
        from_wallet.held_balance -= amount
        from_wallet.updated_at = datetime.utcnow()
        
        # Update to_wallet (add to available)
        to_balance_before = to_wallet.available_balance
        to_wallet.available_balance += artist_amount
        to_wallet.total_earned += artist_amount
        to_wallet.updated_at = datetime.utcnow()
        
        transactions = []
        
        # Create transaction for payer (from held balance)
        payer_tx = await self.create_transaction(
            wallet_id=from_wallet.id,
            user_id=from_user_id,
            transaction_type=f"{reference_type}_payment",
            amount=-amount,
            balance_before=from_wallet.held_balance + amount,  # Before deduction
            balance_after=from_wallet.held_balance,
            description=f"Payment: {description}",
            reference_type=reference_type,
            reference_id=reference_id
        )
        transactions.append(payer_tx)
        
        # Create transaction for recipient
        recipient_tx = await self.create_transaction(
            wallet_id=to_wallet.id,
            user_id=to_user_id,
            transaction_type=f"{reference_type}_payment",
            amount=artist_amount,
            balance_before=to_balance_before,
            balance_after=to_wallet.available_balance,
            description=f"Received: {description}",
            reference_type=reference_type,
            reference_id=reference_id
        )
        transactions.append(recipient_tx)
        
        # Create platform fee transaction
        if platform_fee > 0:
            fee_tx = await self.create_transaction(
                wallet_id=from_wallet.id,
                user_id=from_user_id,
                transaction_type="platform_fee",
                amount=-platform_fee,
                balance_before=from_wallet.held_balance,
                balance_after=from_wallet.held_balance,
                description=f"Platform fee (7.5%): {description}",
                reference_type=reference_type,
                reference_id=reference_id
            )
            transactions.append(fee_tx)
        
        await self.db.commit()
        await self.db.refresh(from_wallet)
        await self.db.refresh(to_wallet)
        
        return from_wallet, to_wallet, transactions
    
    async def refund_held_funds(
        self,
        user_id: UUID,
        amount: Decimal,
        description: str,
        reference_type: str,
        reference_id: UUID
    ) -> Tuple[Wallet, WalletTransaction]:
        """Refund held funds back to available balance"""
        wallet = await self.get_or_create_wallet(user_id)
        
        if wallet.held_balance < amount:
            raise ValueError(f"Insufficient held balance. Held: {wallet.held_balance}, Required: {amount}")
        
        balance_before = wallet.available_balance
        balance_after = balance_before + amount
        
        # Update wallet
        wallet.held_balance -= amount
        wallet.available_balance = balance_after
        wallet.updated_at = datetime.utcnow()
        
        # Create transaction
        transaction = await self.create_transaction(
            wallet_id=wallet.id,
            user_id=user_id,
            transaction_type=f"{reference_type}_refund",
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=f"Refund: {description}",
            reference_type=reference_type,
            reference_id=reference_id
        )
        
        await self.db.commit()
        await self.db.refresh(wallet)
        
        return wallet, transaction
