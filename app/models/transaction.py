from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    buyer_id: UUID = Field(foreign_key="users.id")
    seller_id: UUID = Field(foreign_key="users.id")
    model_id: UUID = Field(foreign_key="models.id")
    amount: float
    platform_fee: float  # 7.5%
    seller_amount: float  # amount - platform_fee
    payment_method: str  # card, paypal, crypto
    payment_status: str  # pending, completed, failed, refunded
    transaction_id: str = Field(unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class Purchase(SQLModel, table=True):
    __tablename__ = "purchases"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    model_id: UUID = Field(foreign_key="models.id")
    transaction_id: UUID = Field(foreign_key="transactions.id")
    download_count: int = Field(default=0)
    download_limit: int = Field(default=10)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Cart(SQLModel, table=True):
    __tablename__ = "cart"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    model_id: UUID = Field(foreign_key="models.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
