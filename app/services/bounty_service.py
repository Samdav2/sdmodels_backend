from typing import Optional, List
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.repositories.bounty_repository import BountyRepository
from app.repositories.user_repository import UserRepository
from app.repositories.wallet_repository import WalletRepository
from app.schemas.bounty import (
    BountyCreate, BountyUpdate, BountyResponse,
    BountyApplicationCreate, BountyApplicationResponse,
    BountySubmissionCreate, BountySubmissionResponse,
    BountyStatsResponse, BountyListResponse, ApplicationListResponse,
    MilestoneCreate, MilestoneResponse,
    DeadlineExtensionRequestCreate, DeadlineExtensionRequestResponse
)
from app.models.bounty import Bounty, BountyApplication, BountySubmission, BountyMilestone, DeadlineExtensionRequest
from app.utils.file_utils import generate_secure_filename, get_file_extension, get_content_type
from app.utils.opendrive_storage import opendrive_storage
import json
from uuid import UUID
from decimal import Decimal


class BountyService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.bounty_repo = BountyRepository(db)
        self.user_repo = UserRepository(db)
        self.wallet_repo = WalletRepository(db)
    
    async def _enrich_bounty_response(self, bounty: Bounty) -> BountyResponse:
        """Add additional fields to bounty response"""
        bounty_dict = bounty.model_dump()
        
        # Parse JSON fields
        if isinstance(bounty_dict.get("requirements"), str):
            bounty_dict["requirements"] = json.loads(bounty_dict["requirements"])
        
        # Get poster username
        poster = await self.user_repo.get_by_id(bounty.poster_id)
        bounty_dict["poster_username"] = poster.username if poster else None
        
        # Get claimed by username
        if bounty.claimed_by_id:
            claimed_by = await self.user_repo.get_by_id(bounty.claimed_by_id)
            bounty_dict["claimed_by_username"] = claimed_by.username if claimed_by else None
        
        # Get applications count
        applications = await self.bounty_repo.get_bounty_applications(bounty.id)
        bounty_dict["applications_count"] = len(applications)
        
        # Get milestones if bounty has them
        if bounty.has_milestones:
            milestones = await self.bounty_repo.get_bounty_milestones(bounty.id)
            bounty_dict["milestones"] = [
                MilestoneResponse(**m.model_dump()) for m in milestones
            ]
        
        return BountyResponse(**bounty_dict)
    
    async def _enrich_application_response(self, application: BountyApplication) -> BountyApplicationResponse:
        """Add additional fields to application response"""
        app_dict = application.model_dump()
        
        # Parse JSON fields
        if isinstance(app_dict.get("portfolio_links"), str):
            app_dict["portfolio_links"] = json.loads(app_dict["portfolio_links"])
        
        # Get applicant details
        applicant = await self.user_repo.get_by_id(application.applicant_id)
        if applicant:
            app_dict["applicant_username"] = applicant.username
            app_dict["applicant_avatar"] = applicant.avatar_url
            app_dict["applicant_rating"] = applicant.rating
        
        return BountyApplicationResponse(**app_dict)
    
    async def _enrich_submission_response(self, submission: BountySubmission) -> BountySubmissionResponse:
        """Add additional fields to submission response"""
        sub_dict = submission.model_dump()
        
        # Parse JSON fields
        if isinstance(sub_dict.get("preview_images"), str):
            sub_dict["preview_images"] = json.loads(sub_dict["preview_images"])
        
        # Get artist username
        artist = await self.user_repo.get_by_id(submission.artist_id)
        sub_dict["artist_username"] = artist.username if artist else None
        
        return BountySubmissionResponse(**sub_dict)
    
    def _validate_model_file(self, file: UploadFile) -> None:
        """Validate model file format and size"""
        # Supported 3D model formats
        SUPPORTED_FORMATS = {
            '.glb', '.gltf', '.fbx', '.obj', '.blend', 
            '.dae', '.stl', '.3ds', '.ply'
        }
        
        # Max file size: 100MB
        MAX_SIZE = 100 * 1024 * 1024
        
        # Get file extension
        ext = get_file_extension(file.filename)
        
        if ext not in SUPPORTED_FORMATS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format. Supported formats: {', '.join(SUPPORTED_FORMATS)}"
            )
        
        # Check file size (if available)
        if hasattr(file, 'size') and file.size and file.size > MAX_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: 100MB"
            )
    
    def _validate_preview_image(self, file: UploadFile) -> None:
        """Validate preview image format and size"""
        # Supported image formats
        SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.webp'}
        
        # Max file size: 10MB
        MAX_SIZE = 10 * 1024 * 1024
        
        # Get file extension
        ext = get_file_extension(file.filename)
        
        if ext not in SUPPORTED_FORMATS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported image format. Supported formats: {', '.join(SUPPORTED_FORMATS)}"
            )
        
        # Check file size (if available)
        if hasattr(file, 'size') and file.size and file.size > MAX_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image too large. Maximum size: 10MB"
            )
    
    async def _upload_model_file(self, file: UploadFile) -> tuple[str, str, int]:
        """
        Upload model file to storage
        Returns: (file_url, secure_filename, file_size)
        """
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Generate secure filename
        secure_filename = generate_secure_filename(file.filename)
        
        # Get content type
        content_type = get_content_type(file.filename)
        
        # Upload to OpenDrive
        file_url = await opendrive_storage.upload_file(
            file_content=content,
            file_name=secure_filename,
            content_type=content_type,
            folder="bounty_submissions"
        )
        
        if not file_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file to storage"
            )
        
        return file_url, secure_filename, file_size
    
    async def _upload_preview_images(self, files: List[UploadFile]) -> List[str]:
        """
        Upload preview images to storage
        Returns: List of image URLs
        """
        if len(files) > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 5 preview images allowed"
            )
        
        image_urls = []
        for file in files:
            # Validate image
            self._validate_preview_image(file)
            
            # Read file content
            content = await file.read()
            
            # Generate secure filename
            secure_filename = generate_secure_filename(file.filename)
            
            # Get content type
            content_type = get_content_type(file.filename)
            
            # Upload to OpenDrive
            file_url = await opendrive_storage.upload_file(
                file_content=content,
                file_name=secure_filename,
                content_type=content_type,
                folder="bounty_previews"
            )
            
            if file_url:
                image_urls.append(file_url)
        
        return image_urls
    
    # Bounty Management
    async def create_bounty(self, bounty_data: BountyCreate, user_id: UUID) -> BountyResponse:
        """Create a new bounty and hold payment in escrow"""
        # Check wallet balance first
        wallet = await self.wallet_repo.get_or_create_wallet(user_id)
        required_amount = Decimal(str(bounty_data.budget))
        
        if wallet.available_balance < required_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient wallet balance. Available: ${wallet.available_balance}, Required: ${required_amount}. Please deposit at least ${required_amount - wallet.available_balance} to create this bounty."
            )
        
        # Create bounty
        bounty = await self.bounty_repo.create_bounty(bounty_data, user_id)
        
        # Hold funds in wallet escrow
        await self.wallet_repo.hold_funds(
            user_id=user_id,
            amount=required_amount,
            description=f"Escrow for bounty: {bounty_data.title}",
            reference_type="bounty",
            reference_id=bounty.id
        )
        
        # Create milestones if provided
        if bounty_data.has_milestones and bounty_data.milestones:
            total_milestone_amount = 0
            for milestone_data in bounty_data.milestones:
                milestone_dict = milestone_data.model_dump()
                # Create milestone and get the created milestone with ID
                created_milestone = await self.bounty_repo.create_milestone(bounty.id, milestone_dict)
                total_milestone_amount += milestone_data.amount
                
                # Create escrow record for tracking (funds already held in wallet)
                await self.bounty_repo.create_milestone_escrow(
                    bounty.id,
                    created_milestone.id,
                    user_id,
                    milestone_data.amount
                )
            
            # Validate total milestone amount matches bounty budget
            if abs(total_milestone_amount - bounty_data.budget) > 0.01:
                # Refund the held funds
                await self.wallet_repo.refund_held_funds(
                    user_id=user_id,
                    amount=required_amount,
                    description=f"Refund: Invalid milestone amounts for bounty {bounty.id}",
                    reference_type="bounty",
                    reference_id=bounty.id
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Total milestone amount ({total_milestone_amount}) must equal bounty budget ({bounty_data.budget})"
                )
        else:
            # Create single escrow transaction record for entire bounty
            await self.bounty_repo.create_escrow(bounty.id, user_id, bounty_data.budget)
        
        return await self._enrich_bounty_response(bounty)
    
    async def get_bounty(self, bounty_id: UUID) -> BountyResponse:
        """Get a single bounty by ID"""
        bounty = await self.bounty_repo.get_bounty(bounty_id)
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        return await self._enrich_bounty_response(bounty)
    
    async def get_bounties(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> BountyListResponse:
        """Get all bounties with filters"""
        skip = (page - 1) * limit
        bounties, total = await self.bounty_repo.get_bounties(status, category, difficulty, skip, limit)
        
        bounty_responses = []
        for b in bounties:
            bounty_responses.append(await self._enrich_bounty_response(b))
        
        return BountyListResponse(
            bounties=bounty_responses,
            total=total,
            page=page,
            limit=limit
        )
    
    async def get_my_posted_bounties(self, user_id: UUID) -> List[BountyResponse]:
        """Get all bounties posted by the user"""
        bounties = await self.bounty_repo.get_my_posted_bounties(user_id)
        return [await self._enrich_bounty_response(b) for b in bounties]
    
    async def get_my_claimed_bounties(self, user_id: UUID) -> List[BountyResponse]:
        """Get all bounties claimed by the user"""
        bounties = await self.bounty_repo.get_my_claimed_bounties(user_id)
        return [await self._enrich_bounty_response(b) for b in bounties]
    
    async def update_bounty(self, bounty_id: UUID, bounty_data: BountyUpdate, user_id: UUID) -> BountyResponse:
        """Update a bounty (owner only)"""
        bounty = await self.bounty_repo.get_bounty(bounty_id)
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        
        if bounty.poster_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this bounty"
            )
        
        if bounty.status != "open":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only update open bounties"
            )
        
        updated_bounty = await self.bounty_repo.update_bounty(bounty_id, bounty_data)
        return await self._enrich_bounty_response(updated_bounty)
    
    async def cancel_bounty(self, bounty_id: UUID, user_id: UUID) -> dict:
        """Cancel a bounty (owner only)"""
        bounty = await self.bounty_repo.get_bounty(bounty_id)
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        
        if bounty.poster_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to cancel this bounty"
            )
        
        if bounty.status not in ["open", "claimed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only cancel open or claimed bounties"
            )
        
        # Refund held funds back to client's available balance
        await self.wallet_repo.refund_held_funds(
            user_id=user_id,
            amount=Decimal(str(bounty.budget)),
            description=f"Refund: Cancelled bounty - {bounty.title}",
            reference_type="bounty",
            reference_id=bounty.id
        )
        
        # Send email to claimed artist if bounty was claimed
        if bounty.claimed_by_id:
            try:
                from app.utils.email import send_bounty_cancelled_email
                from app.core.config import settings
                from sqlalchemy import select
                from app.models.user import User
                
                artist_result = await self.db.execute(
                    select(User).where(User.id == bounty.claimed_by_id)
                )
                artist = artist_result.scalar_one_or_none()
                
                if artist:
                    await send_bounty_cancelled_email(
                        user_email=artist.email,
                        username=artist.username,
                        bounty_title=bounty.title,
                        cancellation_reason="The bounty poster has cancelled this bounty",
                        bounties_url=f"{settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'}/bounties"
                    )
            except Exception as e:
                print(f"Failed to send bounty cancelled email: {e}")
        
        await self.bounty_repo.delete_bounty(bounty_id)
        return {"message": "Bounty cancelled successfully and funds refunded"}
    
    # Application Management
    async def apply_to_bounty(
        self,
        bounty_id: UUID,
        application_data: BountyApplicationCreate,
        user_id: UUID
    ) -> BountyApplicationResponse:
        """Apply to a bounty"""
        bounty = await self.bounty_repo.get_bounty(bounty_id)
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        
        if bounty.status != "open":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bounty is not open for applications"
            )
        
        if bounty.poster_id == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot apply to your own bounty"
            )
        
        # Check if already applied
        existing_app = await self.bounty_repo.get_user_application(bounty_id, user_id)
        if existing_app:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already applied to this bounty"
            )
        
        application = await self.bounty_repo.create_application(bounty_id, user_id, application_data)
        
        # Send email to bounty poster
        try:
            from app.utils.email import send_bounty_application_received_email
            from app.core.config import settings
            from datetime import datetime
            from sqlalchemy import select
            from app.models.user import User
            
            poster_result = await self.db.execute(
                select(User).where(User.id == bounty.poster_id)
            )
            poster = poster_result.scalar_one_or_none()
            
            applicant_result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            applicant = applicant_result.scalar_one_or_none()
            
            if poster and applicant:
                await send_bounty_application_received_email(
                    user_email=poster.email,
                    username=poster.username,
                    bounty_title=bounty.title,
                    applicant_username=applicant.username,
                    proposed_timeline=application_data.proposed_timeline,
                    application_date=datetime.now().strftime("%Y-%m-%d"),
                    bounty_url=f"{settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'}/bounties/{bounty.id}"
                )
        except Exception as e:
            print(f"Failed to send application received email: {e}")
        
        return await self._enrich_application_response(application)
    
    async def get_bounty_applications(self, bounty_id: UUID, user_id: UUID) -> ApplicationListResponse:
        """Get all applications for a bounty (owner only)"""
        bounty = await self.bounty_repo.get_bounty(bounty_id)
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        
        if bounty.poster_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view applications"
            )
        
        applications = await self.bounty_repo.get_bounty_applications(bounty_id)
        app_responses = []
        for a in applications:
            app_responses.append(await self._enrich_application_response(a))
        
        return ApplicationListResponse(applications=app_responses)
    
    async def approve_application(
        self,
        bounty_id: UUID,
        application_id: UUID,
        user_id: UUID
    ) -> BountyApplicationResponse:
        """Approve an application (owner only)"""
        bounty = await self.bounty_repo.get_bounty(bounty_id)
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        
        if bounty.poster_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to approve applications"
            )
        
        application = await self.bounty_repo.approve_application(application_id)
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        # Send email to applicant
        try:
            from app.utils.email import send_bounty_application_approved_email
            from app.core.config import settings
            from sqlalchemy import select
            from app.models.user import User
            
            applicant_result = await self.db.execute(
                select(User).where(User.id == application.applicant_id)
            )
            applicant = applicant_result.scalar_one_or_none()
            
            poster_result = await self.db.execute(
                select(User).where(User.id == bounty.poster_id)
            )
            poster = poster_result.scalar_one_or_none()
            
            if applicant and poster:
                await send_bounty_application_approved_email(
                    user_email=applicant.email,
                    username=applicant.username,
                    bounty_title=bounty.title,
                    bounty_amount=float(bounty.budget),
                    deadline=bounty.deadline.strftime("%Y-%m-%d"),
                    poster_username=poster.username,
                    bounty_url=f"{settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'}/bounties/{bounty.id}"
                )
        except Exception as e:
            print(f"Failed to send application approved email: {e}")
        
        return await self._enrich_application_response(application)
    
    async def reject_application(
        self,
        bounty_id: UUID,
        application_id: UUID,
        user_id: UUID
    ) -> BountyApplicationResponse:
        """Reject an application (owner only)"""
        bounty = await self.bounty_repo.get_bounty(bounty_id)
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        
        if bounty.poster_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to reject applications"
            )
        
        application = await self.bounty_repo.reject_application(application_id)
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        # Send rejection email to applicant
        try:
            from app.utils.email import send_application_rejected_email
            from app.core.config import settings
            from sqlalchemy import select
            from app.models.user import User
            
            applicant_result = await self.db.execute(
                select(User).where(User.id == application.applicant_id)
            )
            applicant = applicant_result.scalar_one_or_none()
            
            if applicant:
                await send_application_rejected_email(
                    user_email=applicant.email,
                    username=applicant.username,
                    bounty_title=bounty.title,
                    bounties_url=f"{settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'}/bounties"
                )
        except Exception as e:
            print(f"Failed to send application rejected email: {e}")
        
        return await self._enrich_application_response(application)
    
    # Submission Management
    async def submit_work(
        self,
        bounty_id: int,
        submission_data: BountySubmissionCreate,
        user_id: int
    ) -> BountySubmissionResponse:
        """Submit work for a bounty (assigned artist only)"""
        bounty = await self.bounty_repo.get_bounty(bounty_id)
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        
        if bounty.claimed_by_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to submit work for this bounty"
            )
        
        if bounty.status not in ["claimed", "in_progress"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bounty is not in a state to accept submissions"
            )
        
        # Check if already submitted
        existing_submission = await self.bounty_repo.get_bounty_submission(bounty_id)
        if existing_submission and existing_submission.status != "revision_requested":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Work already submitted for this bounty"
            )
        
        submission = await self.bounty_repo.create_submission(bounty_id, user_id, submission_data)
        return await self._enrich_submission_response(submission)
    
    async def get_bounty_submission(self, bounty_id: UUID, user_id: UUID) -> BountySubmissionResponse:
        """Get submission for a bounty"""
        bounty = await self.bounty_repo.get_bounty(bounty_id)
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        
        # Only owner or assigned artist can view
        if bounty.poster_id != user_id and bounty.claimed_by_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this submission"
            )
        
        submission = await self.bounty_repo.get_bounty_submission(bounty_id)
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No submission found for this bounty"
            )
        
        return await self._enrich_submission_response(submission)
    
    async def approve_submission(self, bounty_id: int, submission_id: int, user_id: int) -> BountySubmissionResponse:
        """Approve submission and release payment (owner only)"""
        bounty = await self.bounty_repo.get_bounty(bounty_id)
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        
        if bounty.poster_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to approve submissions"
            )
        
        submission = await self.bounty_repo.approve_submission(submission_id)
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found"
            )
        
        # Release escrow payment
        await self.bounty_repo.release_escrow(bounty_id)
        
        return await self._enrich_submission_response(submission)
    
    async def request_revision(
        self,
        bounty_id: int,
        submission_id: int,
        feedback: str,
        user_id: int
    ) -> BountySubmissionResponse:
        """Request revision on submission (owner only)"""
        bounty = await self.bounty_repo.get_bounty(bounty_id)
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        
        if bounty.poster_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to request revisions"
            )
        
        submission = await self.bounty_repo.request_revision(submission_id, feedback)
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found"
            )
        
        return await self._enrich_submission_response(submission)
    
    async def reject_submission(
        self,
        bounty_id: UUID,
        submission_id: UUID,
        reason: str,
        user_id: UUID
    ) -> BountySubmissionResponse:
        """Reject submission (owner only)"""
        bounty = await self.bounty_repo.get_bounty(bounty_id)
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        
        if bounty.poster_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to reject submissions"
            )
        
        submission = await self.bounty_repo.reject_submission(submission_id, reason)
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found"
            )
        
        return await self._enrich_submission_response(submission)
    
    # Statistics
    async def get_stats(self) -> BountyStatsResponse:
        """Get bounty statistics"""
        stats = await self.bounty_repo.get_stats()
        return BountyStatsResponse(**stats)

    # Milestone Management
    async def get_bounty_milestones(self, bounty_id: UUID) -> List[MilestoneResponse]:
        """Get all milestones for a bounty"""
        bounty = await self.bounty_repo.get_bounty(bounty_id)
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        
        if not bounty.has_milestones:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This bounty does not have milestones"
            )
        
        milestones = await self.bounty_repo.get_bounty_milestones(bounty_id)
        return [MilestoneResponse(**m.model_dump()) for m in milestones]
    
    async def start_milestone(self, bounty_id: UUID, milestone_id: UUID, user_id: UUID) -> MilestoneResponse:
        """Start working on a milestone (assigned artist only)"""
        bounty = await self.bounty_repo.get_bounty(bounty_id)
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        
        if bounty.claimed_by_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to work on this bounty"
            )
        
        milestone = await self.bounty_repo.update_milestone_status(milestone_id, "in_progress")
        if not milestone:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Milestone not found"
            )
        
        return MilestoneResponse(**milestone.model_dump())
    
    # Deadline Extension Management
    async def request_deadline_extension(
        self,
        bounty_id: UUID,
        extension_data: DeadlineExtensionRequestCreate,
        user_id: UUID
    ) -> DeadlineExtensionRequestResponse:
        """Request deadline extension (assigned artist only)"""
        bounty = await self.bounty_repo.get_bounty(bounty_id)
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        
        if bounty.claimed_by_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to request extension for this bounty"
            )
        
        # Get current deadline
        if extension_data.milestone_id:
            milestone = await self.bounty_repo.get_milestone(extension_data.milestone_id)
            if not milestone:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Milestone not found"
                )
            current_deadline = milestone.deadline
        else:
            current_deadline = bounty.deadline
        
        # Validate requested deadline is after current deadline
        if extension_data.requested_deadline <= current_deadline:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Requested deadline must be after current deadline"
            )
        
        request = await self.bounty_repo.create_deadline_extension_request(
            bounty_id,
            user_id,
            current_deadline,
            extension_data.requested_deadline,
            extension_data.reason,
            extension_data.milestone_id
        )
        
        return DeadlineExtensionRequestResponse(**request.model_dump())
    
    async def get_extension_requests(self, bounty_id: UUID, user_id: UUID) -> List[DeadlineExtensionRequestResponse]:
        """Get all deadline extension requests for a bounty (owner only)"""
        bounty = await self.bounty_repo.get_bounty(bounty_id)
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        
        if bounty.poster_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view extension requests"
            )
        
        requests = await self.bounty_repo.get_bounty_extension_requests(bounty_id)
        return [DeadlineExtensionRequestResponse(**r.model_dump()) for r in requests]
    
    async def approve_extension_request(
        self,
        bounty_id: UUID,
        request_id: UUID,
        response_message: Optional[str],
        user_id: UUID
    ) -> DeadlineExtensionRequestResponse:
        """Approve deadline extension request (owner only)"""
        bounty = await self.bounty_repo.get_bounty(bounty_id)
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        
        if bounty.poster_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to approve extension requests"
            )
        
        request = await self.bounty_repo.approve_deadline_extension(request_id, response_message)
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Extension request not found"
            )
        
        return DeadlineExtensionRequestResponse(**request.model_dump())
    
    async def reject_extension_request(
        self,
        bounty_id: UUID,
        request_id: UUID,
        response_message: Optional[str],
        user_id: UUID
    ) -> DeadlineExtensionRequestResponse:
        """Reject deadline extension request (owner only)"""
        bounty = await self.bounty_repo.get_bounty(bounty_id)
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        
        if bounty.poster_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to reject extension requests"
            )
        
        request = await self.bounty_repo.reject_deadline_extension(request_id, response_message)
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Extension request not found"
            )
        
        return DeadlineExtensionRequestResponse(**request.model_dump())
    
    # Enhanced Submission with File Upload Support
    async def submit_work(
        self,
        bounty_id: UUID,
        user_id: UUID,
        submission_type: str,
        notes: Optional[str] = None,
        milestone_id: Optional[UUID] = None,
        # For file uploads
        model_file: Optional[UploadFile] = None,
        preview_images: Optional[List[UploadFile]] = None,
        # For external links
        external_model_url: Optional[str] = None,
        preview_image_urls: Optional[List[str]] = None
    ) -> BountySubmissionResponse:
        """Submit work for a bounty (assigned artist only)"""
        bounty = await self.bounty_repo.get_bounty(bounty_id)
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        
        if bounty.claimed_by_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to submit work for this bounty"
            )
        
        if bounty.status not in ["claimed", "in_progress"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bounty is not in a state to accept submissions"
            )
        
        # Check revision limit
        if bounty.revision_count >= bounty.max_revisions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum revision limit ({bounty.max_revisions}) reached"
            )
        
        # Prepare submission data
        submission_data = {
            "submission_type": submission_type,
            "notes": notes,
            "milestone_id": milestone_id
        }
        
        # Handle file upload
        if submission_type == "upload":
            if not model_file:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Model file is required for upload submission"
                )
            
            # Validate model file
            self._validate_model_file(model_file)
            
            # Upload model file
            file_url, secure_filename, file_size = await self._upload_model_file(model_file)
            
            # Get file format
            file_format = get_file_extension(model_file.filename).lstrip('.')
            
            submission_data.update({
                "model_file_url": file_url,
                "model_file_name": model_file.filename,
                "model_file_size": file_size,
                "model_format": file_format
            })
            
            # Upload preview images if provided
            if preview_images:
                image_urls = await self._upload_preview_images(preview_images)
                submission_data["preview_images"] = image_urls
            else:
                submission_data["preview_images"] = []
        
        # Handle external link
        elif submission_type == "link":
            if not external_model_url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="External model URL is required for link submission"
                )
            
            submission_data.update({
                "external_model_url": external_model_url,
                "preview_images": preview_image_urls or []
            })
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid submission type. Must be 'upload' or 'link'"
            )
        
        # Create submission
        submission = await self.bounty_repo.create_submission(bounty_id, user_id, submission_data)
        
        # Update milestone status if applicable
        if milestone_id:
            await self.bounty_repo.update_milestone_status(milestone_id, "submitted")
        
        # Send email to bounty poster
        try:
            from app.utils.email import send_bounty_submission_received_email
            from app.core.config import settings
            from datetime import datetime
            from sqlalchemy import select
            from app.models.user import User
            
            poster_result = await self.db.execute(
                select(User).where(User.id == bounty.poster_id)
            )
            poster = poster_result.scalar_one_or_none()
            
            creator_result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            creator = creator_result.scalar_one_or_none()
            
            if poster and creator:
                await send_bounty_submission_received_email(
                    user_email=poster.email,
                    username=poster.username,
                    bounty_title=bounty.title,
                    creator_username=creator.username,
                    submission_date=datetime.now().strftime("%Y-%m-%d"),
                    bounty_amount=float(bounty.budget),
                    submission_url=f"{settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'}/bounties/{bounty.id}/submission"
                )
        except Exception as e:
            print(f"Failed to send submission received email: {e}")
        
        return await self._enrich_submission_response(submission)
    
    async def approve_submission(self, bounty_id: UUID, submission_id: UUID, user_id: UUID) -> BountySubmissionResponse:
        """Approve submission and release payment (owner only)"""
        bounty = await self.bounty_repo.get_bounty(bounty_id)
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        
        if bounty.poster_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to approve submissions"
            )
        
        submission = await self.bounty_repo.approve_submission(submission_id)
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found"
            )
        
        # Release payment through wallet system
        amount = Decimal(str(bounty.budget))
        if submission.milestone_id:
            # Get milestone amount
            milestone = await self.bounty_repo.get_milestone(submission.milestone_id)
            if milestone:
                amount = Decimal(str(milestone.amount))
            
            await self.bounty_repo.release_milestone_escrow(bounty_id, submission.milestone_id)
            await self.bounty_repo.update_milestone_status(submission.milestone_id, "completed")
        else:
            await self.bounty_repo.release_escrow(bounty_id)
        
        # Release funds from client's held balance to artist's available balance
        await self.wallet_repo.release_funds(
            from_user_id=bounty.poster_id,
            to_user_id=bounty.claimed_by_id,
            amount=amount,
            platform_fee=amount * Decimal("0.075"),  # 7.5% platform fee
            description=f"Payment for bounty: {bounty.title}",
            reference_type="bounty",
            reference_id=bounty.id
        )
        
        # Send email to creator
        try:
            from app.utils.email import send_bounty_submission_approved_email
            from app.core.config import settings
            from sqlalchemy import select
            from app.models.user import User
            
            creator_result = await self.db.execute(
                select(User).where(User.id == bounty.claimed_by_id)
            )
            creator = creator_result.scalar_one_or_none()
            
            if creator:
                await send_bounty_submission_approved_email(
                    user_email=creator.email,
                    username=creator.username,
                    bounty_amount=float(amount),
                    wallet_url=f"{settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'}/wallet"
                )
        except Exception as e:
            print(f"Failed to send submission approved email: {e}")
        
        return await self._enrich_submission_response(submission)
    
    async def request_revision(
        self,
        bounty_id: UUID,
        submission_id: UUID,
        feedback: str,
        user_id: UUID
    ) -> BountySubmissionResponse:
        """Request revision on submission (owner only)"""
        bounty = await self.bounty_repo.get_bounty(bounty_id)
        if not bounty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bounty not found"
            )
        
        if bounty.poster_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to request revisions"
            )
        
        # Check revision limit
        if bounty.revision_count >= bounty.max_revisions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum revision limit ({bounty.max_revisions}) reached. Please approve or reject."
            )
        
        submission = await self.bounty_repo.request_revision(submission_id, feedback)
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found"
            )
        
        # Increment revision count
        bounty.revision_count += 1
        bounty.updated_at = datetime.utcnow()
        await self.bounty_repo.db.commit()
        
        # Send email to creator
        try:
            from app.utils.email import send_bounty_revision_requested_email
            from app.core.config import settings
            from sqlalchemy import select
            from app.models.user import User
            
            creator_result = await self.db.execute(
                select(User).where(User.id == bounty.claimed_by_id)
            )
            creator = creator_result.scalar_one_or_none()
            
            poster_result = await self.db.execute(
                select(User).where(User.id == bounty.poster_id)
            )
            poster = poster_result.scalar_one_or_none()
            
            if creator and poster:
                await send_bounty_revision_requested_email(
                    user_email=creator.email,
                    username=creator.username,
                    poster_username=poster.username,
                    feedback=feedback,
                    bounty_url=f"{settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'}/bounties/{bounty.id}"
                )
        except Exception as e:
            print(f"Failed to send revision requested email: {e}")
        
        return await self._enrich_submission_response(submission)
