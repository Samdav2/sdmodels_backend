"""
Payment models for Paystack (fiat) and NOWPayments (crypto)
"""
from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
from decimal import Decimal
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy import Numeric


class Payment(SQLModel, table=True):
    """Paystack payment records"""
    __tablename__ = "payments"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    wallet_id: Optional[UUID] = Field(default=None, foreign_key="wallets.id")

    # Payment details
    reference: str = Field(unique=True, index=True)
    amount: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    currency: str = Field(default="NGN", max_length=3)

    # Status
    status: str = Field(default="pending", max_length=20)  # pending, success, failed
    payment_type: str = Field(default="deposit", max_length=20)  # deposit, withdrawal

    # Payment gateway info
    channel: Optional[str] = None  # card, bank, ussd, etc.
    paid_at: Optional[datetime] = None

    # Metadata
    payment_metadata: str = Field(default="{}", sa_column=Column(JSON))

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CryptoPayment(SQLModel, table=True):
    """NOWPayments crypto payment records"""
    __tablename__ = "crypto_payments"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    wallet_id: Optional[UUID] = Field(default=None, foreign_key="wallets.id")

    # NOWPayments IDs
    payment_id: Optional[str] = Field(default=None, unique=True, index=True)
    invoice_id: Optional[str] = Field(default=None, unique=True, index=True)
    order_id: str = Field(index=True)

    # Payment details
    order_description: Optional[str] = None
    price_amount: Decimal = Field(sa_column=Column(Numeric(18, 8), nullable=False))
    price_currency: str = Field(max_length=10)
    pay_amount: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(18, 8), nullable=True))
    pay_currency: Optional[str] = Field(default=None, max_length=10)
    actually_paid: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(18, 8), nullable=True))

    # Payment type
    payment_type: str = Field(default="deposit", max_length=20)  # deposit, withdrawal, payout

    # Addresses
    pay_address: Optional[str] = None
    payin_extra_id: Optional[str] = None

    # Payout info (for withdrawals)
    payout_id: Optional[str] = Field(default=None, index=True)
    payout_address: Optional[str] = None
    payout_extra_id: Optional[str] = None

    # Outcome (for conversions)
    outcome_amount: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(18, 8), nullable=True))
    outcome_currency: Optional[str] = Field(default=None, max_length=10)

    # Status
    payment_status: str = Field(default="waiting", max_length=20)
    # waiting, confirming, confirmed, sending, partially_paid, finished, failed, refunded, expired

    # URLs
    invoice_url: Optional[str] = None
    ipn_callback_url: Optional[str] = None

    # Settings
    is_fixed_rate: bool = Field(default=False)
    is_fee_paid_by_user: bool = Field(default=False)

    # Timestamps
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WithdrawalRequest(SQLModel, table=True):
    """Withdrawal requests (both fiat and crypto)"""
    __tablename__ = "withdrawal_requests"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    wallet_id: UUID = Field(foreign_key="wallets.id")

    # Withdrawal details
    amount: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    currency: str = Field(max_length=10)
    withdrawal_method: str = Field(max_length=20)  # paystack, crypto

    # Status
    status: str = Field(default="pending", max_length=20)
    # pending, processing, completed, failed, cancelled

    # Payment reference
    payment_id: Optional[UUID] = Field(default=None, foreign_key="payments.id")
    crypto_payment_id: Optional[UUID] = Field(default=None, foreign_key="crypto_payments.id")

    # Bank details (for Paystack)
    bank_code: Optional[str] = None
    account_number: Optional[str] = None
    account_name: Optional[str] = None

    # Crypto details (for NOWPayments)
    crypto_address: Optional[str] = None
    crypto_currency: Optional[str] = None
    crypto_extra_id: Optional[str] = None

    # Processing info
    processed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None

    # Metadata
    withdrawal_metadata: str = Field(default="{}", sa_column=Column(JSON))

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
