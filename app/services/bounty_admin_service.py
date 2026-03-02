from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.bounty_repository import BountyRepository
from app.repositories.bounty_admin_repository import BountyAdminRepository
from app.repositories.user_repository import UserRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.bounty import BountyResponse
from app.schemas.bounty_admin import (
    BountyDisputeCreate, BountyDisputeResponse,
    DisputeResolutionCreate, DisputeResolutionResponse,
    BountySettingsUpdate, BountySettingsResponse,
    UserBountyBanCreate, UserBountyBanResponse,
    AdminBountyStatsResponse, AdminBountyDetailsResponse,
    BountyStatusUpdate, BountyForceClose, BountyRefund
)
import json


class BountyAdminService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.bounty_repo = BountyRepository(db)
        self.admin_repo = BountyAdminRepository(db)
        self.user_repo = UserRepository(db)
        self.transaction_repo = TransactionRepository(db)
    
    # Bounty Management
    async def get_all_bounties(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> dict:
        skip = (page - 1) * limit
        bounties, total = await self.admin_repo.get_all_bounties_admin(status, search, skip, limit)
        
        bounty_list = []
        for b in bounties:
            bounty_dict = b.model_dump()
            if isinstance(bounty_dict.get("requirements"), str):
                bounty_dict["requirements"] = json.loads(bounty_dict["requirements"])
            
            # Get poster username
            poster = await self.user_repo.get_by_id(b.poster_id)
            bounty_dict["poster_username"] = poster.username if poster else None
            
            bounty_list.append(bounty_dict)
        
        return {
            "bounties": bounty_list,
            "total": total,
            "page": page,
            "limit": limit
        }
    
    async def get_bounty_details(self, bounty_id: int) -> AdminBountyDetailsResponse:
        bounty = await self.bounty_repo.get_bounty(bounty_id)
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        
        # Get bounty data
        bounty_dict = bounty.model_dump()
        if isinstance(bounty_dict.get("requirements"), str):
            bounty_dict["requirements"] = json.loads(bounty_dict["requirements"])
        
        # Get applications
        applications = await self.bounty_repo.get_bounty_applications(bounty_id)
        app_list = [app.model_dump() for app in applications]
        
        # Get submission
        submission = await self.bounty_repo.get_bounty_submission(bounty_id)
        submission_dict = submission.model_dump() if submission else None
        
        # Get dispute
        dispute = await self.admin_repo.get_bounty_dispute(bounty_id)
        dispute_dict = None
        if dispute:
            dispute_dict = dispute.model_dump()
        
        # Get transactions
        transactions = []  # TODO: Implement transaction retrieval
        
        return AdminBountyDetailsResponse(
            bounty=bounty_dict,
            applications=app_list,
            submission=submission_dict,
            dispute=dispute_dict,
            transactions=transactions
        )
    
    async def update_bounty_status(
        self,
        bounty_id: int,
        status_data: BountyStatusUpdate,
        admin_id: int
    ) -> BountyResponse:
        bounty = await self.admin_repo.update_bounty_status_admin(
            bounty_id,
            status_data.status,
            admin_id
        )
        
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        
        bounty_dict = bounty.model_dump()
        if isinstance(bounty_dict.get("requirements"), str):
            bounty_dict["requirements"] = json.loads(bounty_dict["requirements"])
        
        return BountyResponse(**bounty_dict)
    
    async def force_close_bounty(
        self,
        bounty_id: int,
        close_data: BountyForceClose,
        admin_id: int
    ) -> dict:
        bounty = await self.admin_repo.force_close_bounty(
            bounty_id,
            close_data.reason,
            admin_id
        )
        
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        
        # Refund escrow if exists
        escrow = await self.bounty_repo.release_escrow(bounty_id)
        
        return {
            "message": "Bounty force closed successfully",
            "bounty_id": bounty_id,
            "refunded": escrow is not None
        }
    
    async def approve_payout(self, bounty_id: int, admin_id: int) -> dict:
        bounty = await self.bounty_repo.get_bounty(bounty_id)
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        
        # Release escrow
        escrow = await self.bounty_repo.release_escrow(bounty_id)
        if not escrow:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No escrow transaction found or already released"
            )
        
        # Update bounty status
        bounty.status = "completed"
        bounty.completed_at = bounty.updated_at
        await self.db.commit()
        
        # Log action
        await self.admin_repo.log_action(
            admin_id=admin_id,
            action_type="manual_payout_approval",
            bounty_id=bounty_id,
            details={"amount": float(escrow.amount)}
        )
        
        return {
            "message": "Payout approved successfully",
            "transaction_id": escrow.id,
            "amount": float(escrow.amount)
        }
    
    async def refund_bounty(
        self,
        bounty_id: int,
        refund_data: BountyRefund,
        admin_id: int
    ) -> dict:
        bounty = await self.bounty_repo.get_bounty(bounty_id)
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        
        # Cancel bounty
        bounty.status = "cancelled"
        await self.db.commit()
        
        # Log action
        await self.admin_repo.log_action(
            admin_id=admin_id,
            action_type="refund",
            bounty_id=bounty_id,
            details={"reason": refund_data.reason}
        )
        
        return {
            "message": "Bounty refunded successfully",
            "bounty_id": bounty_id
        }
    
    # Dispute Management
    async def get_disputes(self, status: Optional[str] = None) -> List[BountyDisputeResponse]:
        disputes = await self.admin_repo.get_all_disputes(status)
        
        dispute_list = []
        for dispute in disputes:
            dispute_dict = dispute.model_dump()
            
            # Get bounty
            bounty = await self.bounty_repo.get_bounty(dispute.bounty_id)
            if bounty:
                dispute_dict["bounty_title"] = bounty.title
                
                # Get buyer and artist
                poster = await self.user_repo.get_by_id(bounty.poster_id)
                dispute_dict["buyer_username"] = poster.username if poster else None
                
                if bounty.claimed_by_id:
                    artist = await self.user_repo.get_by_id(bounty.claimed_by_id)
                    dispute_dict["artist_username"] = artist.username if artist else None
            
            # Get raised by user
            raised_by = await self.user_repo.get_by_id(dispute.raised_by_id)
            dispute_dict["raised_by_username"] = raised_by.username if raised_by else None
            
            dispute_list.append(BountyDisputeResponse(**dispute_dict))
        
        return dispute_list
    
    async def resolve_dispute(
        self,
        bounty_id: int,
        resolution_data: DisputeResolutionCreate,
        admin_id: int
    ) -> DisputeResolutionResponse:
        # Get dispute
        dispute = await self.admin_repo.get_bounty_dispute(bounty_id)
        if not dispute:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active dispute found for this bounty"
            )
        
        # Get bounty
        bounty = await self.bounty_repo.get_bounty(bounty_id)
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        
        # Resolve dispute
        resolution = await self.admin_repo.resolve_dispute(
            dispute.id,
            admin_id,
            resolution_data
        )
        
        # Handle payment based on winner
        if resolution_data.winner == "artist":
            # Release payment to artist
            await self.bounty_repo.release_escrow(bounty_id)
            bounty.status = "completed"
        else:
            # Refund to buyer (partial or full based on percentage)
            bounty.status = "cancelled"
            # TODO: Implement partial refund logic
        
        await self.db.commit()
        
        # Log action
        await self.admin_repo.log_action(
            admin_id=admin_id,
            action_type="dispute_resolution",
            bounty_id=bounty_id,
            details={
                "winner": resolution_data.winner,
                "refund_percentage": resolution_data.refund_percentage
            }
        )
        
        # Send email notifications to both parties
        try:
            from app.utils.email import send_dispute_resolved_email
            from app.core.config import settings
            from sqlalchemy import select
            from app.models.user import User
            
            # Notify buyer (poster)
            poster_result = await self.db.execute(
                select(User).where(User.id == bounty.poster_id)
            )
            poster = poster_result.scalar_one_or_none()
            
            if poster:
                await send_dispute_resolved_email(
                    user_email=poster.email,
                    username=poster.username,
                    bounty_title=bounty.title,
                    resolution_decision=f"Resolved in favor of: {resolution_data.winner}",
                    resolution_notes=resolution_data.notes or "The dispute has been resolved by our admin team.",
                    bounty_url=f"{settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'}/bounties/{bounty_id}"
                )
            
            # Notify artist (claimed_by)
            if bounty.claimed_by_id:
                artist_result = await self.db.execute(
                    select(User).where(User.id == bounty.claimed_by_id)
                )
                artist = artist_result.scalar_one_or_none()
                
                if artist:
                    await send_dispute_resolved_email(
                        user_email=artist.email,
                        username=artist.username,
                        bounty_title=bounty.title,
                        resolution_decision=f"Resolved in favor of: {resolution_data.winner}",
                        resolution_notes=resolution_data.notes or "The dispute has been resolved by our admin team.",
                        bounty_url=f"{settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'}/bounties/{bounty_id}"
                    )
        except Exception as e:
            print(f"Failed to send dispute resolved emails: {e}")
        
        return DisputeResolutionResponse(**resolution.model_dump())
    
    # Settings Management
    async def get_settings(self) -> BountySettingsResponse:
        settings = await self.admin_repo.get_settings()
        if not settings:
            # Return defaults
            return BountySettingsResponse(
                id=0,
                min_bounty_amount=10.00,
                max_bounty_amount=10000.00,
                platform_fee_percentage=7.50,
                escrow_hold_days=3,
                auto_approve_after_days=14,
                updated_at=None,
                updated_by_admin_id=None
            )
        return BountySettingsResponse(**settings.model_dump())
    
    async def update_settings(
        self,
        settings_data: BountySettingsUpdate,
        admin_id: int
    ) -> BountySettingsResponse:
        # Validate min < max
        if settings_data.min_bounty_amount and settings_data.max_bounty_amount:
            if settings_data.min_bounty_amount >= settings_data.max_bounty_amount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Minimum bounty amount must be less than maximum"
                )
        
        settings = await self.admin_repo.update_settings(settings_data, admin_id)
        
        # Log action
        await self.admin_repo.log_action(
            admin_id=admin_id,
            action_type="settings_update",
            details=settings_data.model_dump(exclude_unset=True)
        )
        
        return BountySettingsResponse(**settings.model_dump())
    
    # User Ban Management
    async def ban_user(
        self,
        ban_data: UserBountyBanCreate,
        admin_id: int
    ) -> UserBountyBanResponse:
        # Check if already banned
        existing_ban = await self.admin_repo.get_user_ban(ban_data.user_id)
        if existing_ban:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already banned from bounties"
            )
        
        # Create ban
        ban = await self.admin_repo.ban_user(ban_data, admin_id)
        
        # Cancel all active bounties for this user
        posted_bounties = await self.bounty_repo.get_my_posted_bounties(ban_data.user_id)
        for bounty in posted_bounties:
            if bounty.status in ["open", "claimed", "in_progress"]:
                await self.admin_repo.force_close_bounty(
                    bounty.id,
                    f"User banned: {ban_data.reason}",
                    admin_id
                )
        
        # Log action
        await self.admin_repo.log_action(
            admin_id=admin_id,
            action_type="user_ban",
            details={
                "user_id": ban_data.user_id,
                "reason": ban_data.reason,
                "duration_days": ban_data.duration_days
            }
        )
        
        ban_dict = ban.model_dump()
        
        # Get usernames
        user = await self.user_repo.get_by_id(ban_data.user_id)
        ban_dict["user_username"] = user.username if user else None
        
        admin = await self.user_repo.get_by_id(admin_id)
        ban_dict["banned_by_username"] = admin.username if admin else None
        
        # Send email notification to banned user
        if user:
            try:
                from app.utils.email import send_user_banned_email
                from app.core.config import settings
                
                duration_text = f"{ban_data.duration_days} days" if ban_data.duration_days else "Permanent"
                
                await send_user_banned_email(
                    user_email=user.email,
                    username=user.username,
                    restriction_type="bounty participation",
                    reason=ban_data.reason,
                    duration=duration_text,
                    support_url=f"{settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'}/support"
                )
            except Exception as e:
                print(f"Failed to send user banned email: {e}")
        
        return UserBountyBanResponse(**ban_dict)
    
    # Statistics
    async def get_stats(self) -> AdminBountyStatsResponse:
        stats = await self.admin_repo.get_admin_stats()
        return AdminBountyStatsResponse(**stats)
