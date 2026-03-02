from uuid import UUID
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status, File, Form, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.services.bounty_service import BountyService
from app.schemas.bounty import (
    BountyCreate, BountyUpdate, BountyResponse, BountyListResponse,
    BountyApplicationCreate, BountyApplicationResponse, ApplicationListResponse,
    BountySubmissionCreate, BountySubmissionResponse, BountySubmissionReview,
    BountyStatsResponse, MilestoneResponse,
    DeadlineExtensionRequestCreate, DeadlineExtensionRequestResponse, DeadlineExtensionReview
)

router = APIRouter()


# Bounty Management Endpoints
@router.post("/", response_model=BountyResponse, status_code=status.HTTP_201_CREATED)
async def create_bounty(
    bounty_data: BountyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new bounty with escrow protection."""
    service = BountyService(db)
    return await service.create_bounty(bounty_data, current_user.id)


@router.get("/", response_model=BountyListResponse)
async def get_bounties(
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db)
):
    """Get all bounties with optional filters."""
    service = BountyService(db)
    return await service.get_bounties(status, category, difficulty, page, limit)


@router.get("/stats", response_model=BountyStatsResponse)
async def get_bounty_stats(db: AsyncSession = Depends(get_db)):
    """Get bounty platform statistics."""
    service = BountyService(db)
    return await service.get_stats()


@router.get("/my-posted", response_model=list[BountyResponse])
async def get_my_posted_bounties(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all bounties posted by the current user."""
    service = BountyService(db)
    return await service.get_my_posted_bounties(current_user.id)


@router.get("/my-claimed", response_model=list[BountyResponse])
async def get_my_claimed_bounties(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all bounties claimed by the current user."""
    service = BountyService(db)
    return await service.get_my_claimed_bounties(current_user.id)


@router.get("/{bounty_id}", response_model=BountyResponse)
async def get_bounty(
    bounty_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a single bounty by ID."""
    service = BountyService(db)
    return await service.get_bounty(bounty_id)


@router.put("/{bounty_id}", response_model=BountyResponse)
async def update_bounty(
    bounty_id: UUID,
    bounty_data: BountyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a bounty (owner only, open bounties only)."""
    service = BountyService(db)
    return await service.update_bounty(bounty_id, bounty_data, current_user.id)


@router.delete("/{bounty_id}")
async def cancel_bounty(
    bounty_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a bounty (owner only)."""
    service = BountyService(db)
    return await service.cancel_bounty(bounty_id, current_user.id)


# Application Management Endpoints
@router.post("/{bounty_id}/apply", response_model=BountyApplicationResponse, status_code=status.HTTP_201_CREATED)
async def apply_to_bounty(
    bounty_id: UUID,
    application_data: BountyApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Apply to a bounty as an artist."""
    service = BountyService(db)
    return await service.apply_to_bounty(bounty_id, application_data, current_user.id)


@router.get("/{bounty_id}/applications", response_model=ApplicationListResponse)
async def get_bounty_applications(
    bounty_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all applications for a bounty (owner only)."""
    service = BountyService(db)
    return await service.get_bounty_applications(bounty_id, current_user.id)


@router.post("/{bounty_id}/applications/{application_id}/approve", response_model=BountyApplicationResponse)
async def approve_application(
    bounty_id: UUID,
    application_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Approve an application (owner only)."""
    service = BountyService(db)
    return await service.approve_application(bounty_id, application_id, current_user.id)


@router.post("/{bounty_id}/applications/{application_id}/reject", response_model=BountyApplicationResponse)
async def reject_application(
    bounty_id: UUID,
    application_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reject an application (owner only)."""
    service = BountyService(db)
    return await service.reject_application(bounty_id, application_id, current_user.id)


# Submission Management Endpoints
@router.post("/{bounty_id}/submit", response_model=BountySubmissionResponse, status_code=status.HTTP_201_CREATED)
async def submit_work(
    bounty_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    # Form fields
    submission_type: str = Form(...),
    notes: Optional[str] = Form(None),
    milestone_id: Optional[str] = Form(None),
    # For file uploads
    model_file: Optional[UploadFile] = File(None),
    preview_images: Optional[List[UploadFile]] = File(None),
    # For external links
    external_model_url: Optional[str] = Form(None),
    preview_image_urls: Optional[str] = Form(None)  # JSON string of URLs
):
    """
    Submit completed work for a bounty (assigned artist only).
    
    Supports two submission types:
    1. File Upload: Upload model file and preview images
    2. External Link: Provide URL to model hosted elsewhere (Sketchfab, ArtStation, etc.)
    """
    service = BountyService(db)
    
    # Parse milestone_id if provided
    parsed_milestone_id = None
    if milestone_id:
        try:
            parsed_milestone_id = UUID(milestone_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid milestone_id format"
            )
    
    # Parse preview_image_urls if provided
    parsed_preview_urls = None
    if preview_image_urls:
        try:
            import json
            parsed_preview_urls = json.loads(preview_image_urls)
        except:
            parsed_preview_urls = [preview_image_urls]  # Single URL
    
    return await service.submit_work(
        bounty_id=bounty_id,
        user_id=current_user.id,
        submission_type=submission_type,
        notes=notes,
        milestone_id=parsed_milestone_id,
        model_file=model_file,
        preview_images=preview_images,
        external_model_url=external_model_url,
        preview_image_urls=parsed_preview_urls
    )


@router.get("/{bounty_id}/submission", response_model=BountySubmissionResponse)
async def get_bounty_submission(
    bounty_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get submission for a bounty (owner or assigned artist only)."""
    service = BountyService(db)
    return await service.get_bounty_submission(bounty_id, current_user.id)


@router.post("/{bounty_id}/submissions/{submission_id}/approve", response_model=BountySubmissionResponse)
async def approve_submission(
    bounty_id: UUID,
    submission_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Approve submission and release escrow payment (owner only)."""
    service = BountyService(db)
    return await service.approve_submission(bounty_id, submission_id, current_user.id)


@router.post("/{bounty_id}/submissions/{submission_id}/revision", response_model=BountySubmissionResponse)
async def request_revision(
    bounty_id: UUID,
    submission_id: UUID,
    review_data: BountySubmissionReview,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Request revision on submission (owner only)."""
    service = BountyService(db)
    return await service.request_revision(
        bounty_id,
        submission_id,
        review_data.feedback or "",
        current_user.id
    )


@router.post("/{bounty_id}/submissions/{submission_id}/reject", response_model=BountySubmissionResponse)
async def reject_submission(
    bounty_id: UUID,
    submission_id: UUID,
    review_data: BountySubmissionReview,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reject submission (owner only)."""
    service = BountyService(db)
    return await service.reject_submission(
        bounty_id,
        submission_id,
        review_data.feedback or "",
        current_user.id
    )


# Milestone Management Endpoints
@router.get("/{bounty_id}/milestones", response_model=list[MilestoneResponse])
async def get_bounty_milestones(
    bounty_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all milestones for a bounty."""
    service = BountyService(db)
    return await service.get_bounty_milestones(bounty_id)


@router.post("/{bounty_id}/milestones/{milestone_id}/start", response_model=MilestoneResponse)
async def start_milestone(
    bounty_id: UUID,
    milestone_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start working on a milestone (assigned artist only)."""
    service = BountyService(db)
    return await service.start_milestone(bounty_id, milestone_id, current_user.id)


# Deadline Extension Endpoints
@router.post("/{bounty_id}/request-extension", response_model=DeadlineExtensionRequestResponse, status_code=status.HTTP_201_CREATED)
async def request_deadline_extension(
    bounty_id: UUID,
    extension_data: DeadlineExtensionRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Request deadline extension (assigned artist only)."""
    service = BountyService(db)
    return await service.request_deadline_extension(bounty_id, extension_data, current_user.id)


@router.get("/{bounty_id}/extension-requests", response_model=list[DeadlineExtensionRequestResponse])
async def get_extension_requests(
    bounty_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all deadline extension requests for a bounty (owner only)."""
    service = BountyService(db)
    return await service.get_extension_requests(bounty_id, current_user.id)


@router.post("/{bounty_id}/extension-requests/{request_id}/approve", response_model=DeadlineExtensionRequestResponse)
async def approve_extension_request(
    bounty_id: UUID,
    request_id: UUID,
    review_data: DeadlineExtensionReview,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Approve deadline extension request (owner only)."""
    service = BountyService(db)
    return await service.approve_extension_request(
        bounty_id,
        request_id,
        review_data.response_message,
        current_user.id
    )


@router.post("/{bounty_id}/extension-requests/{request_id}/reject", response_model=DeadlineExtensionRequestResponse)
async def reject_extension_request(
    bounty_id: UUID,
    request_id: UUID,
    review_data: DeadlineExtensionReview,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reject deadline extension request (owner only)."""
    service = BountyService(db)
    return await service.reject_extension_request(
        bounty_id,
        request_id,
        review_data.response_message,
        current_user.id
    )
