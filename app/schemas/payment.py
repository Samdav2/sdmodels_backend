"""
Payment schemas for Paystack and NOWPayments
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, Field


# ============= Paystack Schemas =============

class PaystackInitializeRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Amount in main currency unit (e.g., Naira)")
    email: str
    callback_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PaystackInitializeResponse(BaseModel):
    authorization_url: str
    access_code: str
    reference: str


class PaystackVerifyResponse(BaseModel):
    status: str
    message: str
    data: Dict[str, Any]


class PaystackTransferRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    recipient_code: str
    reason: Optional[str] = None


class PaystackRecipientRequest(BaseModel):
    type: str = "nuban"  # nuban, mobile_money, basa
    name: str
    account_number: str
    bank_code: str
    currency: str = "NGN"


# ============= NOWPayments Schemas =============

class NOWPaymentsInvoiceRequest(BaseModel):
    price_amount: Decimal = Field(..., gt=0)
    price_currency: str
    pay_currency: Optional[str] = None
    ipn_callback_url: Optional[str] = None
    order_id: str
    order_description: Optional[str] = None
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None
    is_fixed_rate: bool = False
    is_fee_paid_by_user: bool = False


class NOWPaymentsPaymentRequest(BaseModel):
    price_amount: Decimal = Field(..., gt=0)
    price_currency: str
    pay_currency: str
    ipn_callback_url: Optional[str] = None
    order_id: str
    order_description: Optional[str] = None
    is_fixed_rate: bool = False
    is_fee_paid_by_user: bool = False


class NOWPaymentsIPNPayload(BaseModel):
    payment_id: Optional[int] = None
    invoice_id: Optional[int] = None
    payment_status: str
    pay_address: Optional[str] = None
    price_amount: Optional[Decimal] = None
    price_currency: Optional[str] = None
    pay_amount: Optional[Decimal] = None
    pay_currency: Optional[str] = None
    actually_paid: Optional[Decimal] = None
    outcome_amount: Optional[Decimal] = None
    outcome_currency: Optional[str] = None
    payin_extra_id: Optional[str] = None


class CryptoPaymentCreate(BaseModel):
    user_id: UUID
    payment_id: Optional[str] = None
    invoice_id: Optional[str] = None
    order_id: str
    order_description: Optional[str] = None
    price_amount: Decimal
    price_currency: str
    pay_amount: Optional[Decimal] = None
    pay_currency: Optional[str] = None
    pay_address: Optional[str] = None
    payin_extra_id: Optional[str] = None
    ipn_callback_url: Optional[str] = None
    invoice_url: Optional[str] = None
    is_fixed_rate: bool = False
    is_fee_paid_by_user: bool = False
    payment_status: str = "waiting"
    created_at: Optional[datetime] = None


class CryptoPaymentUpdate(BaseModel):
    payment_status: Optional[str] = None
    pay_address: Optional[str] = None
    pay_amount: Optional[Decimal] = None
    actually_paid: Optional[Decimal] = None
    payin_extra_id: Optional[str] = None
    outcome_amount: Optional[Decimal] = None
    outcome_currency: Optional[str] = None


class CryptoPaymentResponse(BaseModel):
    id: UUID
    user_id: UUID
    payment_id: Optional[str]
    invoice_id: Optional[str]
    order_id: str
    price_amount: Decimal
    price_currency: str
    pay_amount: Optional[Decimal]
    pay_currency: Optional[str]
    pay_address: Optional[str]
    payment_status: str
    invoice_url: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============= Withdrawal Schemas =============

class WithdrawalRequestCreate(BaseModel):
    amount: Decimal = Field(..., gt=0)
    withdrawal_method: str = Field(..., description="paystack or crypto")
    
    # For Paystack
    bank_code: Optional[str] = None
    account_number: Optional[str] = None
    account_name: Optional[str] = None
    
    # For Crypto
    crypto_address: Optional[str] = None
    crypto_currency: Optional[str] = None
    crypto_extra_id: Optional[str] = None


class WithdrawalRequestResponse(BaseModel):
    id: UUID
    user_id: UUID
    amount: Decimal
    currency: str
    withdrawal_method: str
    status: str
    created_at: datetime
    
    # Payment references
    payment_id: Optional[UUID] = None
    crypto_payment_id: Optional[UUID] = None
    
    # Bank details
    bank_code: Optional[str] = None
    account_number: Optional[str] = None
    account_name: Optional[str] = None
    
    # Crypto details
    crypto_address: Optional[str] = None
    crypto_currency: Optional[str] = None
    
    class Config:
        from_attributes = True


# ============= Deposit Schemas =============

class DepositRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    payment_method: str = Field(..., description="paystack or crypto")
    currency: str = Field(default="NGN", description="NGN for Paystack, BTC/ETH/USDT for crypto")
    callback_url: Optional[str] = None


class DepositResponse(BaseModel):
    payment_id: UUID
    amount: Decimal
    currency: str
    payment_method: str
    status: str
    
    # Paystack
    authorization_url: Optional[str] = None
    reference: Optional[str] = None
    
    # Crypto
    invoice_url: Optional[str] = None
    pay_address: Optional[str] = None
    pay_amount: Optional[Decimal] = None
    pay_currency: Optional[str] = None


# ============= Available Currencies =============

class AvailableCurrency(BaseModel):
    code: str
    name: str
    network: Optional[str] = None
    is_popular: bool = False


class AvailableCurrenciesResponse(BaseModel):
    fiat: List[AvailableCurrency]
    crypto: List[AvailableCurrency]


# ============= Payment Status =============

class PaymentStatusResponse(BaseModel):
    payment_id: UUID
    status: str
    amount: Decimal
    currency: str
    payment_method: str
    created_at: datetime
    paid_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
