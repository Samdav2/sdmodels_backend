from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


# Dispute Schemas
class BountyDisputeCreate(BaseModel):
    bounty_id: UUID
    reason: str = Field(..., min_length=20)


class BountyDisputeResponse(BaseModel):
    id: UUID
    bounty_id: UUID
    raised_by_id: UUID
    raised_by_role: str
    reason: str
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by_admin_id: Optional[UUID] = None
    
    # Enriched fields
    bounty_title: Optional[str] = None
    raised_by_username: Optional[str] = None
    buyer_username: Optional[str] = None
    artist_username: Optional[str] = None
    
    class Config:
        from_attributes = True


# Dispute Resolution Schemas
class DisputeResolutionCreate(BaseModel):
    winner: str = Field(..., pattern="^(buyer|artist)$")
    refund_percentage: Optional[int] = Field(None, ge=0, le=100)
    notes: str = Field(..., min_length=20)


class DisputeResolutionResponse(BaseModel):
    id: UUID
    dispute_id: UUID
    bounty_id: UUID
    admin_id: UUID
    winner: str
    refund_percentage: Optional[int] = None
    notes: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Bounty Settings Schemas
class BountySettingsUpdate(BaseModel):
    min_bounty_amount: Optional[float] = Field(None, gt=0)
    max_bounty_amount: Optional[float] = Field(None, gt=0)
    platform_fee_percentage: Optional[float] = Field(None, ge=0, le=100)
    escrow_hold_days: Optional[int] = Field(None, ge=0)
    auto_approve_after_days: Optional[int] = Field(None, ge=0)


class BountySettingsResponse(BaseModel):
    id: UUID
    min_bounty_amount: float
    max_bounty_amount: float
    platform_fee_percentage: float
    escrow_hold_days: int
    auto_approve_after_days: int
    updated_at: datetime
    updated_by_admin_id: Optional[UUID] = None
    
    class Config:
        from_attributes = True


# User Ban Schemas
class UserBountyBanCreate(BaseModel):
    user_id: UUID
    reason: str = Field(..., min_length=10)
    duration_days: Optional[int] = Field(None, gt=0)


class UserBountyBanResponse(BaseModel):
    id: UUID
    user_id: UUID
    banned_by_admin_id: UUID
    reason: str
    banned_at: datetime
    expires_at: Optional[datetime] = None
    is_permanent: bool
    
    # Enriched fields
    user_username: Optional[str] = None
    banned_by_username: Optional[str] = None
    
    class Config:
        from_attributes = True


# Admin Action Schemas
class AdminBountyActionResponse(BaseModel):
    id: UUID
    admin_id: UUID
    bounty_id: Optional[UUID] = None
    action_type: str
    details: dict
    created_at: datetime
    
    # Enriched fields
    admin_username: Optional[str] = None
    
    class Config:
        from_attributes = True


# Admin Bounty Stats
class AdminBountyStatsResponse(BaseModel):
    total_bounties: int
    active_bounties: int
    total_value: float
    disputed_bounties: int
    completed_bounties: int
    total_platform_fees: float
    average_bounty_amount: float


# Admin Bounty Details
class AdminBountyDetailsResponse(BaseModel):
    bounty: dict
    applications: List[dict]
    submission: Optional[dict] = None
    dispute: Optional[BountyDisputeResponse] = None
    transactions: List[dict]


# Status Update
class BountyStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(open|claimed|in_progress|submitted|completed|cancelled)$")


# Force Close
class BountyForceClose(BaseModel):
    reason: str = Field(..., min_length=10)


# Refund
class BountyRefund(BaseModel):
    reason: str = Field(..., min_length=10)
