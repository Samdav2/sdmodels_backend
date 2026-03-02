from uuid import UUID
from typing import Optional, List
from datetime import datetime, date
from sqlmodel import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.bounty import Bounty, BountyApplication, BountySubmission, EscrowTransaction
from app.schemas.bounty import BountyCreate, BountyUpdate, BountyApplicationCreate, BountySubmissionCreate
import json


class BountyRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # Bounty CRUD
    async def create_bounty(self, bounty_data: BountyCreate, poster_id: UUID) -> Bounty:
        # Convert bounty_data to dict and handle requirements separately
        bounty_dict = bounty_data.model_dump(exclude={'requirements'})
        
        bounty = Bounty(
            **bounty_dict,
            poster_id=poster_id,
            requirements=json.dumps(bounty_data.requirements)
        )
        self.db.add(bounty)
        await self.db.commit()
        await self.db.refresh(bounty)
        return bounty
    
    async def get_bounty(self, bounty_id: UUID) -> Optional[Bounty]:
        return await self.db.get(Bounty, bounty_id)
    
    async def get_bounties(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[Bounty], int]:
        query = select(Bounty)
        
        filters = []
        if status:
            filters.append(Bounty.status == status)
        if category:
            filters.append(Bounty.category == category)
        if difficulty:
            filters.append(Bounty.difficulty == difficulty)
        
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
    
    async def get_my_posted_bounties(self, user_id: UUID) -> List[Bounty]:
        query = select(Bounty).where(Bounty.poster_id == user_id).order_by(Bounty.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_my_claimed_bounties(self, user_id: UUID) -> List[Bounty]:
        query = select(Bounty).where(Bounty.claimed_by_id == user_id).order_by(Bounty.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update_bounty(self, bounty_id: UUID, bounty_data: BountyUpdate) -> Optional[Bounty]:
        bounty = await self.get_bounty(bounty_id)
        if not bounty:
            return None
        
        update_data = bounty_data.model_dump(exclude_unset=True)
        if "requirements" in update_data:
            update_data["requirements"] = json.dumps(update_data["requirements"])
        
        for key, value in update_data.items():
            setattr(bounty, key, value)
        
        bounty.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(bounty)
        return bounty
    
    async def delete_bounty(self, bounty_id: UUID) -> bool:
        bounty = await self.get_bounty(bounty_id)
        if not bounty:
            return False
        
        bounty.status = "cancelled"
        bounty.updated_at = datetime.utcnow()
        await self.db.commit()
        return True
    
    # Application CRUD
    async def create_application(
        self,
        bounty_id: UUID,
        applicant_id: UUID,
        application_data: BountyApplicationCreate
    ) -> BountyApplication:
        application = BountyApplication(
            bounty_id=bounty_id,
            applicant_id=applicant_id,
            proposal=application_data.proposal,
            estimated_delivery=application_data.estimated_delivery,
            portfolio_links=json.dumps(application_data.portfolio_links)
        )
        self.db.add(application)
        await self.db.commit()
        await self.db.refresh(application)
        return application
    
    async def get_application(self, application_id: UUID) -> Optional[BountyApplication]:
        return await self.db.get(BountyApplication, application_id)
    
    async def get_bounty_applications(self, bounty_id: UUID) -> List[BountyApplication]:
        query = select(BountyApplication).where(
            BountyApplication.bounty_id == bounty_id
        ).order_by(BountyApplication.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_user_application(self, bounty_id: UUID, user_id: UUID) -> Optional[BountyApplication]:
        query = select(BountyApplication).where(
            and_(
                BountyApplication.bounty_id == bounty_id,
                BountyApplication.applicant_id == user_id
            )
        )
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def approve_application(self, application_id: UUID) -> Optional[BountyApplication]:
        application = await self.get_application(application_id)
        if not application:
            return None
        
        # Update application status
        application.status = "approved"
        
        # Update bounty
        bounty = await self.get_bounty(application.bounty_id)
        if bounty:
            bounty.status = "claimed"
            bounty.claimed_by_id = application.applicant_id
            bounty.claimed_at = datetime.utcnow()
            bounty.updated_at = datetime.utcnow()
        
        # Reject all other pending applications
        other_apps_query = select(BountyApplication).where(
            and_(
                BountyApplication.bounty_id == application.bounty_id,
                BountyApplication.id != application_id,
                BountyApplication.status == "pending"
            )
        )
        result = await self.db.execute(other_apps_query)
        for app in result.scalars().all():
            app.status = "rejected"
        
        await self.db.commit()
        await self.db.refresh(application)
        return application
    
    async def reject_application(self, application_id: UUID) -> Optional[BountyApplication]:
        application = await self.get_application(application_id)
        if not application:
            return None
        
        application.status = "rejected"
        await self.db.commit()
        await self.db.refresh(application)
        return application
    
    # Submission CRUD
    async def create_submission(
        self,
        bounty_id: UUID,
        artist_id: UUID,
        submission_data: dict
    ) -> BountySubmission:
        # Handle preview_images
        preview_images = submission_data.pop("preview_images", [])
        if isinstance(preview_images, list):
            preview_images = json.dumps(preview_images)
        
        submission = BountySubmission(
            bounty_id=bounty_id,
            artist_id=artist_id,
            preview_images=preview_images,
            **submission_data
        )
        self.db.add(submission)
        
        # Update bounty status
        bounty = await self.get_bounty(bounty_id)
        if bounty:
            bounty.status = "submitted"
            bounty.submitted_at = datetime.utcnow()
            bounty.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(submission)
        return submission
    
    async def get_submission(self, submission_id: UUID) -> Optional[BountySubmission]:
        return await self.db.get(BountySubmission, submission_id)
    
    async def get_bounty_submission(self, bounty_id: UUID) -> Optional[BountySubmission]:
        query = select(BountySubmission).where(BountySubmission.bounty_id == bounty_id)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def approve_submission(self, submission_id: UUID) -> Optional[BountySubmission]:
        submission = await self.get_submission(submission_id)
        if not submission:
            return None
        
        submission.status = "approved"
        submission.reviewed_at = datetime.utcnow()
        
        # Update bounty
        bounty = await self.get_bounty(submission.bounty_id)
        if bounty:
            bounty.status = "completed"
            bounty.completed_at = datetime.utcnow()
            bounty.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(submission)
        return submission
    
    async def request_revision(self, submission_id: UUID, feedback: str) -> Optional[BountySubmission]:
        submission = await self.get_submission(submission_id)
        if not submission:
            return None
        
        submission.status = "revision_requested"
        submission.feedback = feedback
        submission.reviewed_at = datetime.utcnow()
        
        # Update bounty status back to in_progress
        bounty = await self.get_bounty(submission.bounty_id)
        if bounty:
            bounty.status = "in_progress"
            bounty.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(submission)
        return submission
    
    async def reject_submission(self, submission_id: UUID, reason: str) -> Optional[BountySubmission]:
        submission = await self.get_submission(submission_id)
        if not submission:
            return None
        
        submission.status = "rejected"
        submission.feedback = reason
        submission.reviewed_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(submission)
        return submission
    
    # Escrow CRUD
    async def create_escrow(self, bounty_id: UUID, buyer_id: UUID, amount: float) -> EscrowTransaction:
        platform_fee = amount * 0.075  # 7.5% platform fee
        
        escrow = EscrowTransaction(
            bounty_id=bounty_id,
            buyer_id=buyer_id,
            amount=amount,
            platform_fee=platform_fee
        )
        self.db.add(escrow)
        await self.db.commit()
        await self.db.refresh(escrow)
        return escrow
    
    async def release_escrow(self, bounty_id: UUID) -> Optional[EscrowTransaction]:
        query = select(EscrowTransaction).where(
            and_(
                EscrowTransaction.bounty_id == bounty_id,
                EscrowTransaction.status == "held"
            )
        )
        result = await self.db.execute(query)
        escrow = result.scalars().first()
        
        if not escrow:
            return None
        
        bounty = await self.get_bounty(bounty_id)
        if bounty and bounty.claimed_by_id:
            escrow.artist_id = bounty.claimed_by_id
            escrow.status = "released"
            escrow.released_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(escrow)
        
        return escrow
    
    # Statistics
    async def get_stats(self) -> dict:
        total_bounties_result = await self.db.execute(select(func.count()).select_from(Bounty))
        total_bounties = total_bounties_result.scalar_one()
        
        open_bounties_result = await self.db.execute(
            select(func.count()).select_from(Bounty).where(Bounty.status == "open")
        )
        open_bounties = open_bounties_result.scalar_one()
        
        completed_bounties_result = await self.db.execute(
            select(func.count()).select_from(Bounty).where(Bounty.status == "completed")
        )
        completed_bounties = completed_bounties_result.scalar_one()
        
        total_value_result = await self.db.execute(select(func.sum(Bounty.budget)).select_from(Bounty))
        total_value = total_value_result.scalar_one()
        total_value = float(total_value) if total_value else 0.0
        
        avg_budget_result = await self.db.execute(select(func.avg(Bounty.budget)).select_from(Bounty))
        avg_budget = avg_budget_result.scalar_one()
        average_budget = float(avg_budget) if avg_budget else 0.0
        
        active_artists_result = await self.db.execute(
            select(func.count(func.distinct(Bounty.claimed_by_id)))
            .select_from(Bounty)
            .where(Bounty.claimed_by_id.isnot(None))
        )
        active_artists = active_artists_result.scalar_one()
        
        return {
            "total_bounties": total_bounties,
            "open_bounties": open_bounties,
            "total_value": total_value,
            "average_budget": average_budget,
            "completed_bounties": completed_bounties,
            "active_artists": active_artists
        }

    # Milestone CRUD
    async def create_milestone(self, bounty_id: UUID, milestone_data: dict) -> "BountyMilestone":
        from app.models.bounty import BountyMilestone
        milestone = BountyMilestone(
            bounty_id=bounty_id,
            **milestone_data
        )
        self.db.add(milestone)
        await self.db.commit()
        await self.db.refresh(milestone)
        return milestone
    
    async def get_milestone(self, milestone_id: UUID) -> Optional["BountyMilestone"]:
        from app.models.bounty import BountyMilestone
        return await self.db.get(BountyMilestone, milestone_id)
    
    async def get_bounty_milestones(self, bounty_id: UUID) -> List["BountyMilestone"]:
        from app.models.bounty import BountyMilestone
        query = select(BountyMilestone).where(
            BountyMilestone.bounty_id == bounty_id
        ).order_by(BountyMilestone.order)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update_milestone_status(self, milestone_id: UUID, status: str) -> Optional["BountyMilestone"]:
        from app.models.bounty import BountyMilestone
        milestone = await self.get_milestone(milestone_id)
        if not milestone:
            return None
        
        milestone.status = status
        milestone.updated_at = datetime.utcnow()
        
        if status == "in_progress":
            milestone.started_at = datetime.utcnow()
        elif status == "submitted":
            milestone.submitted_at = datetime.utcnow()
        elif status == "completed":
            milestone.completed_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(milestone)
        return milestone
    
    # Deadline Extension CRUD
    async def create_deadline_extension_request(
        self,
        bounty_id: UUID,
        artist_id: UUID,
        current_deadline: date,
        requested_deadline: date,
        reason: str,
        milestone_id: Optional[UUID] = None
    ) -> "DeadlineExtensionRequest":
        from app.models.bounty import DeadlineExtensionRequest
        request = DeadlineExtensionRequest(
            bounty_id=bounty_id,
            milestone_id=milestone_id,
            artist_id=artist_id,
            current_deadline=current_deadline,
            requested_deadline=requested_deadline,
            reason=reason
        )
        self.db.add(request)
        await self.db.commit()
        await self.db.refresh(request)
        return request
    
    async def get_deadline_extension_request(self, request_id: UUID) -> Optional["DeadlineExtensionRequest"]:
        from app.models.bounty import DeadlineExtensionRequest
        return await self.db.get(DeadlineExtensionRequest, request_id)
    
    async def get_bounty_extension_requests(self, bounty_id: UUID) -> List["DeadlineExtensionRequest"]:
        from app.models.bounty import DeadlineExtensionRequest
        query = select(DeadlineExtensionRequest).where(
            DeadlineExtensionRequest.bounty_id == bounty_id
        ).order_by(DeadlineExtensionRequest.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def approve_deadline_extension(
        self,
        request_id: UUID,
        response_message: Optional[str] = None
    ) -> Optional["DeadlineExtensionRequest"]:
        from app.models.bounty import DeadlineExtensionRequest
        request = await self.get_deadline_extension_request(request_id)
        if not request:
            return None
        
        request.status = "approved"
        request.response_message = response_message
        request.responded_at = datetime.utcnow()
        
        # Update the deadline
        if request.milestone_id:
            milestone = await self.get_milestone(request.milestone_id)
            if milestone:
                milestone.deadline = request.requested_deadline
                milestone.updated_at = datetime.utcnow()
        else:
            bounty = await self.get_bounty(request.bounty_id)
            if bounty:
                bounty.deadline = request.requested_deadline
                bounty.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(request)
        return request
    
    async def reject_deadline_extension(
        self,
        request_id: UUID,
        response_message: Optional[str] = None
    ) -> Optional["DeadlineExtensionRequest"]:
        from app.models.bounty import DeadlineExtensionRequest
        request = await self.get_deadline_extension_request(request_id)
        if not request:
            return None
        
        request.status = "rejected"
        request.response_message = response_message
        request.responded_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(request)
        return request
    
    # Enhanced Escrow with Milestone Support
    async def create_milestone_escrow(
        self,
        bounty_id: UUID,
        milestone_id: UUID,
        buyer_id: UUID,
        amount: float
    ) -> EscrowTransaction:
        platform_fee = amount * 0.075  # 7.5% platform fee
        
        escrow = EscrowTransaction(
            bounty_id=bounty_id,
            milestone_id=milestone_id,
            buyer_id=buyer_id,
            amount=amount,
            platform_fee=platform_fee
        )
        self.db.add(escrow)
        await self.db.commit()
        await self.db.refresh(escrow)
        return escrow
    
    async def release_milestone_escrow(
        self,
        bounty_id: UUID,
        milestone_id: UUID
    ) -> Optional[EscrowTransaction]:
        query = select(EscrowTransaction).where(
            and_(
                EscrowTransaction.bounty_id == bounty_id,
                EscrowTransaction.milestone_id == milestone_id,
                EscrowTransaction.status == "held"
            )
        )
        result = await self.db.execute(query)
        escrow = result.scalars().first()
        
        if not escrow:
            return None
        
        bounty = await self.get_bounty(bounty_id)
        if bounty and bounty.claimed_by_id:
            escrow.artist_id = bounty.claimed_by_id
            escrow.status = "released"
            escrow.released_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(escrow)
        
        return escrow
