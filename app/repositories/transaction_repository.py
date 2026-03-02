from uuid import UUID
from typing import Optional, List
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction, Purchase, Cart


class TransactionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_transaction(self, **kwargs) -> Transaction:
        transaction = Transaction(**kwargs)
        self.session.add(transaction)
        await self.session.commit()
        await self.session.refresh(transaction)
        return transaction
    
    async def get_transaction(self, transaction_id: UUID) -> Optional[Transaction]:
        result = await self.session.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_transactions(self, user_id: UUID, skip: int = 0, limit: int = 20) -> List[Transaction]:
        result = await self.session.execute(
            select(Transaction)
            .where((Transaction.buyer_id == user_id) | (Transaction.seller_id == user_id))
            .order_by(Transaction.created_at.desc())
            .offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def create_purchase(self, **kwargs) -> Purchase:
        purchase = Purchase(**kwargs)
        self.session.add(purchase)
        await self.session.commit()
        await self.session.refresh(purchase)
        return purchase
    
    async def get_purchase(self, user_id: UUID, model_id: UUID) -> Optional[Purchase]:
        result = await self.session.execute(
            select(Purchase).where(
                Purchase.user_id == user_id,
                Purchase.model_id == model_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_user_purchases(self, user_id: UUID, skip: int = 0, limit: int = 20) -> List[Purchase]:
        result = await self.session.execute(
            select(Purchase)
            .where(Purchase.user_id == user_id)
            .order_by(Purchase.created_at.desc())
            .offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def increment_download_count(self, purchase_id: int) -> bool:
        result = await self.session.execute(
            select(Purchase).where(Purchase.id == purchase_id)
        )
        purchase = result.scalar_one_or_none()
        
        if not purchase or purchase.download_count >= purchase.download_limit:
            return False
        
        purchase.download_count += 1
        await self.session.commit()
        return True
    
    async def add_to_cart(self, user_id: UUID, model_id: UUID) -> Cart:
        cart_item = Cart(user_id=user_id, model_id=model_id)
        self.session.add(cart_item)
        await self.session.commit()
        await self.session.refresh(cart_item)
        return cart_item
    
    async def get_cart(self, user_id: UUID) -> List[Cart]:
        result = await self.session.execute(
            select(Cart).where(Cart.user_id == user_id)
        )
        return result.scalars().all()
    
    async def remove_from_cart(self, user_id: UUID, model_id: UUID) -> bool:
        result = await self.session.execute(
            select(Cart).where(
                Cart.user_id == user_id,
                Cart.model_id == model_id
            )
        )
        cart_item = result.scalar_one_or_none()
        
        if not cart_item:
            return False
        
        await self.session.delete(cart_item)
        await self.session.commit()
        return True
    
    async def clear_cart(self, user_id: UUID) -> bool:
        result = await self.session.execute(
            select(Cart).where(Cart.user_id == user_id)
        )
        cart_items = result.scalars().all()
        
        for item in cart_items:
            await self.session.delete(item)
        
        await self.session.commit()
        return True
