from typing import Optional, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, Field


# Wallet Schemas
class WalletResponse(BaseModel):
    id: UUID
    user_id: UUID
    available_balance: Decimal
    held_balance: Decimal
    total_balance: Decimal
    total_deposited: Decimal
    total_withdrawn: Decimal
    total_earned: Decimal
    currency: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class WalletBalanceResponse(BaseModel):
    wallet_id: UUID
    available_balance: Decimal
    held_balance: Decimal
    total_balance: Decimal
    currency: str
    total_deposited: Decimal
    total_withdrawn: Decimal
    total_earned: Decimal


# Transaction Schemas
class DepositRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Amount to deposit")
    payment_method: str = Field(..., description="Payment method (paystack, crypto)")
    callback_url: Optional[str] = Field(None, description="URL to redirect after payment")


class WithdrawalRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Amount to withdraw")
    withdrawal_method: str = Field(..., description="Withdrawal method (bank_transfer, paypal, etc.)")
    bank_account_id: Optional[str] = Field(None, description="Bank account ID")


class TransactionResponse(BaseModel):
    id: UUID
    wallet_id: UUID
    user_id: UUID
    transaction_type: str
    amount: Decimal
    balance_before: Decimal
    balance_after: Decimal
    status: str
    description: Optional[str] = None
    reference_type: Optional[str] = None
    reference_id: Optional[UUID] = None
    transaction_metadata: dict = {}
    created_at: datetime
    
    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    transactions: List[TransactionResponse]
    total: int
    page: int
    limit: int


class DepositResponse(BaseModel):
    transaction_id: Optional[UUID] = None
    reference: Optional[str] = None
    amount: Decimal
    authorization_url: Optional[str] = None
    access_code: Optional[str] = None
    new_balance: Decimal
    status: str


class WithdrawalResponse(BaseModel):
    transaction_id: UUID
    amount: Decimal
    new_balance: Decimal
    status: str
    estimated_arrival: Optional[str] = None


# Internal transfer schemas
class InternalTransferRequest(BaseModel):
    from_user_id: UUID
    to_user_id: UUID
    amount: Decimal
    description: str
    reference_type: Optional[str] = None
    reference_id: Optional[UUID] = None
