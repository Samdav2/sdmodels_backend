from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_admin
from app.models.user import User
from app.services.bounty_admin_service import BountyAdminService
from app.schemas.bounty import BountyResponse
from app.schemas.bounty_admin import (
    BountyDisputeResponse, DisputeResolutionCreate, DisputeResolutionResponse,
    BountySettingsUpdate, BountySettingsResponse,
    UserBountyBanCreate, UserBountyBanResponse,
    AdminBountyStatsResponse, AdminBountyDetailsResponse,
    BountyStatusUpdate, BountyForceClose, BountyRefund
)

router = APIRouter()


# Bounty Management Endpoints
@router.get("/bounties", response_model=dict)
async def get_all_bounties_admin(
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by title/description"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all bounties with admin filters (Admin only).
    
    - **status**: Filter by status
    - **search**: Search in title and description
    - **page**: Page number
    - **limit**: Items per page
    """
    service = BountyAdminService(db)
    return await service.get_all_bounties(status, search, page, limit)


@router.get("/bounties/stats", response_model=AdminBountyStatsResponse)
async def get_bounty_stats_admin(
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive bounty statistics (Admin only).
    
    Returns:
    - Total bounties
    - Active bounties
    - Total value
    - Disputed bounties
    - Completed bounties
    - Total platform fees collected
    - Average bounty amount
    """
    service = BountyAdminService(db)
    return await service.get_stats()


@router.get("/bounties/{bounty_id}", response_model=AdminBountyDetailsResponse)
async def get_bounty_details_admin(
    bounty_id: UUID,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed bounty information with all related data (Admin only).
    
    Returns:
    - Bounty details
    - All applications
    - Submission (if exists)
    - Dispute (if exists)
    - Transaction history
    """
    service = BountyAdminService(db)
    return await service.get_bounty_details(bounty_id)


@router.put("/bounties/{bounty_id}/status", response_model=BountyResponse)
async def update_bounty_status_admin(
    bounty_id: UUID,
    status_data: BountyStatusUpdate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update bounty status (Admin only).
    
    Can override any status regardless of current state.
    """
    service = BountyAdminService(db)
    return await service.update_bounty_status(bounty_id, status_data, current_admin.id)


@router.post("/bounties/{bounty_id}/force-close")
async def force_close_bounty(
    bounty_id: UUID,
    close_data: BountyForceClose,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Force close a bounty regardless of status (Admin only).
    
    - Cancels the bounty
    - Refunds buyer if payment in escrow
    - Logs admin action
    """
    service = BountyAdminService(db)
    return await service.force_close_bounty(bounty_id, close_data, current_admin.id)


@router.post("/bounties/{bounty_id}/approve-payout")
async def approve_payout_admin(
    bounty_id: UUID,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually approve and release escrow payment (Admin only).
    
    Overrides normal approval process.
    """
    service = BountyAdminService(db)
    return await service.approve_payout(bounty_id, current_admin.id)


@router.post("/bounties/{bounty_id}/refund")
async def refund_bounty_admin(
    bounty_id: UUID,
    refund_data: BountyRefund,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Issue full refund to buyer (Admin only).
    
    - Cancels bounty
    - Refunds buyer
    - Logs admin action
    """
    service = BountyAdminService(db)
    return await service.refund_bounty(bounty_id, refund_data, current_admin.id)


# Dispute Management Endpoints
@router.get("/bounties/disputes", response_model=list[BountyDisputeResponse])
async def get_bounty_disputes(
    status: Optional[str] = Query(None, description="Filter by status"),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all bounty disputes (Admin only).
    
    - **status**: Filter by dispute status (open, resolved, escalated)
    """
    service = BountyAdminService(db)
    return await service.get_disputes(status)


@router.post("/bounties/{bounty_id}/resolve-dispute", response_model=DisputeResolutionResponse)
async def resolve_bounty_dispute(
    bounty_id: UUID,
    resolution_data: DisputeResolutionCreate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Resolve a bounty dispute (Admin only).
    
    - **winner**: "buyer" or "artist"
    - **refund_percentage**: 0-100 (if buyer wins)
    - **notes**: Resolution explanation (required)
    
    Actions:
    - If artist wins: Release full payment
    - If buyer wins: Refund based on percentage
    - Notify both parties
    - Log resolution
    """
    service = BountyAdminService(db)
    return await service.resolve_dispute(bounty_id, resolution_data, current_admin.id)


# Settings Management Endpoints
@router.get("/bounties/settings", response_model=BountySettingsResponse)
async def get_bounty_settings(
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current bounty system settings (Admin only).
    """
    service = BountyAdminService(db)
    return await service.get_settings()


@router.put("/bounties/settings", response_model=BountySettingsResponse)
async def update_bounty_settings(
    settings_data: BountySettingsUpdate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update bounty system settings (Admin only).
    
    - **min_bounty_amount**: Minimum bounty amount
    - **max_bounty_amount**: Maximum bounty amount
    - **platform_fee_percentage**: Platform fee (0-100)
    - **escrow_hold_days**: Days to hold in escrow
    - **auto_approve_after_days**: Auto-approve after days
    """
    service = BountyAdminService(db)
    return await service.update_settings(settings_data, current_admin.id)


# User Ban Management Endpoints
@router.post("/bounties/ban-user", response_model=UserBountyBanResponse, status_code=status.HTTP_201_CREATED)
async def ban_user_from_bounties(
    ban_data: UserBountyBanCreate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Ban a user from creating/claiming bounties (Admin only).
    
    - **user_id**: User to ban
    - **reason**: Ban reason (required)
    - **duration_days**: Ban duration (optional, permanent if not provided)
    
    Actions:
    - Prevent user from bounty activities
    - Cancel all active bounties
    - Notify user
    - Log action
    """
    service = BountyAdminService(db)
    return await service.ban_user(ban_data, current_admin.id)
