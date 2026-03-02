from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class CartAddRequest(BaseModel):
    model_id: UUID


class CartResponse(BaseModel):
    id: UUID
    user_id: UUID
    model_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class CheckoutRequest(BaseModel):
    model_ids: List[UUID]
    payment_method: str  # card, paypal, crypto
    payment_details: dict
    coupon_code: Optional[str] = None


class TransactionResponse(BaseModel):
    id: UUID
    buyer_id: UUID
    seller_id: UUID
    model_id: UUID
    amount: float
    platform_fee: float
    seller_amount: float
    payment_method: str
    payment_status: str
    transaction_id: str
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class PurchaseResponse(BaseModel):
    id: UUID
    user_id: UUID
    model_id: UUID
    transaction_id: UUID
    download_count: int
    download_limit: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class DownloadLinkResponse(BaseModel):
    download_url: str
    expires_at: datetime
