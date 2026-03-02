from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
from decimal import Decimal
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy import CheckConstraint


class Wallet(SQLModel, table=True):
    __tablename__ = "wallets"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", unique=True, index=True)
    
    # Balances
    available_balance: Decimal = Field(default=Decimal("0.00"), max_digits=10, decimal_places=2)
    held_balance: Decimal = Field(default=Decimal("0.00"), max_digits=10, decimal_places=2)
    
    # Statistics
    total_deposited: Decimal = Field(default=Decimal("0.00"), max_digits=10, decimal_places=2)
    total_withdrawn: Decimal = Field(default=Decimal("0.00"), max_digits=10, decimal_places=2)
    total_earned: Decimal = Field(default=Decimal("0.00"), max_digits=10, decimal_places=2)
    
    # Currency
    currency: str = Field(default="USD", max_length=3)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint("available_balance >= 0", name="positive_available_balance"),
        CheckConstraint("held_balance >= 0", name="positive_held_balance"),
    )


class WalletTransaction(SQLModel, table=True):
    __tablename__ = "wallet_transactions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    wallet_id: UUID = Field(foreign_key="wallets.id", index=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    
    # Transaction details
    transaction_type: str = Field(max_length=50, index=True)
    amount: Decimal = Field(max_digits=10, decimal_places=2)
    
    # Balance tracking
    balance_before: Decimal = Field(max_digits=10, decimal_places=2)
    balance_after: Decimal = Field(max_digits=10, decimal_places=2)
    
    # Status
    status: str = Field(default="completed", max_length=20)
    
    # Description and metadata
    description: Optional[str] = None
    reference_type: Optional[str] = Field(default=None, max_length=50)  # 'bounty', 'model', etc.
    reference_id: Optional[UUID] = None
    transaction_metadata: str = Field(default="{}", sa_column=Column(JSON))
    
    # Timestamp
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint(
            "transaction_type IN ('deposit', 'withdrawal', 'bounty_escrow', 'bounty_payment', "
            "'bounty_refund', 'model_purchase', 'model_sale', 'platform_fee', "
            "'milestone_escrow', 'milestone_payment')",
            name="valid_transaction_type"
        ),
        CheckConstraint(
            "status IN ('pending', 'completed', 'failed', 'cancelled')",
            name="valid_status"
        ),
    )
