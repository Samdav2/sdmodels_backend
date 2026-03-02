from uuid import UUID
from typing import Optional, List
from datetime import datetime, timedelta
from sqlmodel import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.bounty import Bounty, BountyApplication, BountySubmission, EscrowTransaction
from app.models.bounty_admin import (
    BountyDispute, BountyDisputeResolution, BountySettings,
    UserBountyBan, AdminBountyAction
)
from app.schemas.bounty_admin import (
    BountyDisputeCreate, DisputeResolutionCreate,
    BountySettingsUpdate, UserBountyBanCreate
)
import json


class BountyAdminRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # Dispute Management
    async def create_dispute(self, dispute_data: BountyDisputeCreate, raised_by_id: int, role: str) -> BountyDispute:
        dispute = BountyDispute(
            **dispute_data.model_dump(),
            raised_by_id=raised_by_id,
            raised_by_role=role
        )
        self.db.add(dispute)
        await self.db.commit()
        await self.db.refresh(dispute)
        return dispute
    
    async def get_dispute(self, dispute_id: int) -> Optional[BountyDispute]:
        return await self.db.get(BountyDispute, dispute_id)
    
    async def get_bounty_dispute(self, bounty_id: UUID) -> Optional[BountyDispute]:
        query = select(BountyDispute).where(
            and_(
                BountyDispute.bounty_id == bounty_id,
                BountyDispute.status == "open"
            )
        )
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_all_disputes(self, status: Optional[str] = None) -> List[BountyDispute]:
        query = select(BountyDispute)
        if status:
            query = query.where(BountyDispute.status == status)
        query = query.order_by(BountyDispute.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def resolve_dispute(
        self,
        dispute_id: int,
        admin_id: UUID,
        resolution_data: DisputeResolutionCreate
    ) -> BountyDisputeResolution:
        dispute = await self.get_dispute(dispute_id)
        if not dispute:
            return None
        
        # Create resolution
        resolution = BountyDisputeResolution(
            dispute_id=dispute_id,
            bounty_id=dispute.bounty_id,
            admin_id=admin_id,
            **resolution_data.model_dump()
        )
        self.db.add(resolution)
        
        # Update dispute
        dispute.status = "resolved"
        dispute.resolved_at = datetime.utcnow()
        dispute.resolved_by_admin_id = admin_id
        
        await self.db.commit()
        await self.db.refresh(resolution)
        return resolution
    
    # Settings Management
    async def get_settings(self) -> Optional[BountySettings]:
        query = select(BountySettings).order_by(BountySettings.id.desc()).limit(1)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def update_settings(
        self,
        settings_data: BountySettingsUpdate,
        admin_id: int
    ) -> BountySettings:
        current_settings = await self.get_settings()
        
        if current_settings:
            # Update existing
            update_data = settings_data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(current_settings, key, value)
            current_settings.updated_at = datetime.utcnow()
            current_settings.updated_by_admin_id = admin_id
            settings = current_settings
        else:
            # Create new
            settings = BountySettings(
                **settings_data.model_dump(exclude_unset=True),
                updated_by_admin_id=admin_id
            )
            self.db.add(settings)
        
        await self.db.commit()
        await self.db.refresh(settings)
        return settings
    
    # User Ban Management
    async def ban_user(self, ban_data: UserBountyBanCreate, admin_id: UUID) -> UserBountyBan:
        expires_at = None
        is_permanent = True
        
        if ban_data.duration_days:
            expires_at = datetime.utcnow() + timedelta(days=ban_data.duration_days)
            is_permanent = False
        
        ban = UserBountyBan(
            user_id=ban_data.user_id,
            banned_by_admin_id=admin_id,
            reason=ban_data.reason,
            expires_at=expires_at,
            is_permanent=is_permanent
        )
        self.db.add(ban)
        await self.db.commit()
        await self.db.refresh(ban)
        return ban
    
    async def get_user_ban(self, user_id: UUID) -> Optional[UserBountyBan]:
        query = select(UserBountyBan).where(UserBountyBan.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def is_user_banned(self, user_id: UUID) -> bool:
        ban = await self.get_user_ban(user_id)
        if not ban:
            return False
        
        if ban.is_permanent:
            return True
        
        if ban.expires_at and ban.expires_at > datetime.utcnow():
            return True
        
        return False
    
    # Admin Action Logging
    async def log_action(
        self,
        admin_id: UUID,
        action_type: str,
        bounty_id: Optional[UUID] = None,
        details: dict = None
    ) -> AdminBountyAction:
        action = AdminBountyAction(
            admin_id=admin_id,
            bounty_id=bounty_id,
            action_type=action_type,
            details=json.dumps(details or {})
        )
        self.db.add(action)
        await self.db.commit()
        await self.db.refresh(action)
        return action
    
    async def get_bounty_actions(self, bounty_id: UUID) -> List[AdminBountyAction]:
        query = select(AdminBountyAction).where(
            AdminBountyAction.bounty_id == bounty_id
        ).order_by(AdminBountyAction.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    # Admin Statistics
    async def get_admin_stats(self) -> dict:
        # Total bounties
        total_result = await self.db.execute(select(func.count()).select_from(Bounty))
        total_bounties = total_result.scalar_one()
        
        # Active bounties
        active_result = await self.db.execute(
            select(func.count()).select_from(Bounty).where(
                Bounty.status.in_(["open", "claimed", "in_progress", "submitted"])
            )
        )
        active_bounties = active_result.scalar_one()
        
        # Total value
        value_result = await self.db.execute(select(func.sum(Bounty.budget)).select_from(Bounty))
        total_value = value_result.scalar_one()
        total_value = float(total_value) if total_value else 0.0
        
        # Disputed bounties
        disputed_result = await self.db.execute(
            select(func.count()).select_from(BountyDispute).where(BountyDispute.status == "open")
        )
        disputed_bounties = disputed_result.scalar_one()
        
        # Completed bounties
        completed_result = await self.db.execute(
            select(func.count()).select_from(Bounty).where(Bounty.status == "completed")
        )
        completed_bounties = completed_result.scalar_one()
        
        # Total platform fees
        fees_result = await self.db.execute(
            select(func.sum(EscrowTransaction.platform_fee)).select_from(EscrowTransaction).where(
                EscrowTransaction.status == "released"
            )
        )
        total_platform_fees = fees_result.scalar_one()
        total_platform_fees = float(total_platform_fees) if total_platform_fees else 0.0
        
        # Average bounty amount
        avg_result = await self.db.execute(select(func.avg(Bounty.budget)).select_from(Bounty))
        average_bounty_amount = avg_result.scalar_one()
        average_bounty_amount = float(average_bounty_amount) if average_bounty_amount else 0.0
        
        return {
            "total_bounties": total_bounties,
            "active_bounties": active_bounties,
            "total_value": total_value,
            "disputed_bounties": disputed_bounties,
            "completed_bounties": completed_bounties,
            "total_platform_fees": total_platform_fees,
            "average_bounty_amount": average_bounty_amount
        }
    
    # Bounty Management
    async def get_all_bounties_admin(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[Bounty], int]:
        query = select(Bounty)
        
        filters = []
        if status:
            filters.append(Bounty.status == status)
        if search:
            filters.append(
                or_(
                    Bounty.title.ilike(f"%{search}%"),
                    Bounty.description.ilike(f"%{search}%")
                )
            )
        
        if filters:
            query = query.where(and_(*filters))
        
        # Get total count
        count_query = select(func.count()).select_from(Bounty)
        if filters:
            count_query = count_query.where(and_(*filters))
        result = await self.db.execute(count_query)
        total = result.scalar_one()
        
        # Get paginated results
        query = query.order_by(Bounty.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        bounties = result.scalars().all()
        
        return list(bounties), total
    
    async def force_close_bounty(self, bounty_id: UUID, reason: str, admin_id: UUID) -> Bounty:
        bounty = await self.db.get(Bounty, bounty_id)
        if not bounty:
            return None
        
        bounty.status = "cancelled"
        bounty.updated_at = datetime.utcnow()
        
        # Log action
        await self.log_action(
            admin_id=admin_id,
            action_type="force_close",
            bounty_id=bounty_id,
            details={"reason": reason}
        )
        
        await self.db.commit()
        await self.db.refresh(bounty)
        return bounty
    
    async def update_bounty_status_admin(
        self,
        bounty_id: UUID,
        status: str,
        admin_id: int
    ) -> Bounty:
        bounty = await self.db.get(Bounty, bounty_id)
        if not bounty:
            return None
        
        old_status = bounty.status
        bounty.status = status
        bounty.updated_at = datetime.utcnow()
        
        # Log action
        await self.log_action(
            admin_id=admin_id,
            action_type="status_change",
            bounty_id=bounty_id,
            details={"old_status": old_status, "new_status": status}
        )
        
        await self.db.commit()
        await self.db.refresh(bounty)
        return bounty
