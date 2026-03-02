from typing import Optional, List
from datetime import datetime, date
from uuid import UUID
from pydantic import BaseModel, Field


# Forward reference for type hints
class MilestoneResponse(BaseModel):
    pass


# Milestone Schemas
class MilestoneBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: str
    amount: float = Field(..., gt=0)
    deadline: date
    order: int = Field(default=1, ge=1)


class MilestoneCreate(MilestoneBase):
    pass


class MilestoneResponse(MilestoneBase):
    id: UUID
    bounty_id: UUID
    status: str
    started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Bounty Schemas
class BountyBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: str
    budget: float = Field(..., gt=0)
    deadline: date
    category: str = Field(..., max_length=100)
    difficulty: str = Field(..., pattern="^(easy|medium|hard)$")
    requirements: List[str] = Field(default_factory=list)
    has_milestones: bool = Field(default=False)
    max_revisions: int = Field(default=3, ge=0, le=10)


class BountyCreate(BountyBase):
    milestones: Optional[List[MilestoneCreate]] = None


class BountyUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    budget: Optional[float] = Field(None, gt=0)
    deadline: Optional[date] = None
    category: Optional[str] = Field(None, max_length=100)
    difficulty: Optional[str] = Field(None, pattern="^(easy|medium|hard)$")
    requirements: Optional[List[str]] = None


class BountyResponse(BountyBase):
    id: UUID
    status: str
    poster_id: UUID
    claimed_by_id: Optional[UUID] = None
    revision_count: int = 0
    claimed_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Additional fields for frontend
    poster_username: Optional[str] = None
    claimed_by_username: Optional[str] = None
    applications_count: Optional[int] = 0
    milestones: Optional[List[MilestoneResponse]] = None
    
    class Config:
        from_attributes = True


# Application Schemas
class BountyApplicationBase(BaseModel):
    proposal: str = Field(..., min_length=50)
    estimated_delivery: date
    portfolio_links: List[str] = Field(default_factory=list)


class BountyApplicationCreate(BountyApplicationBase):
    pass


class BountyApplicationResponse(BountyApplicationBase):
    id: UUID
    bounty_id: UUID
    applicant_id: UUID
    status: str
    created_at: datetime
    
    # Additional fields
    applicant_username: Optional[str] = None
    applicant_avatar: Optional[str] = None
    applicant_rating: Optional[float] = None
    
    class Config:
        from_attributes = True


# Submission Schemas
class BountySubmissionBase(BaseModel):
    submission_type: str = Field(default="upload", pattern="^(upload|link)$")
    notes: Optional[str] = None
    milestone_id: Optional[UUID] = None


class BountySubmissionCreate(BountySubmissionBase):
    # For external links
    external_model_url: Optional[str] = Field(None, max_length=500)
    preview_images: List[str] = Field(default_factory=list)  # URLs for link submissions
    
    # Note: For file uploads, files are handled separately via multipart/form-data
    # The endpoint will handle: model_file (UploadFile) and preview_images (List[UploadFile])


class BountySubmissionResponse(BaseModel):
    id: UUID
    bounty_id: UUID
    milestone_id: Optional[UUID] = None
    artist_id: UUID
    
    # Submission details
    submission_type: str
    model_file_url: Optional[str] = None
    model_file_name: Optional[str] = None
    model_file_size: Optional[int] = None
    model_format: Optional[str] = None
    external_model_url: Optional[str] = None
    preview_images: List[str] = Field(default_factory=list)
    
    notes: Optional[str] = None
    status: str
    feedback: Optional[str] = None
    revision_number: int = 1
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None
    
    # Additional fields
    artist_username: Optional[str] = None
    
    class Config:
        from_attributes = True


class BountySubmissionReview(BaseModel):
    feedback: Optional[str] = None


# Deadline Extension Schemas
class DeadlineExtensionRequestCreate(BaseModel):
    milestone_id: Optional[UUID] = None
    requested_deadline: date
    reason: str = Field(..., min_length=20)


class DeadlineExtensionRequestResponse(BaseModel):
    id: UUID
    bounty_id: UUID
    milestone_id: Optional[UUID] = None
    artist_id: UUID
    current_deadline: date
    requested_deadline: date
    reason: str
    status: str
    response_message: Optional[str] = None
    created_at: datetime
    responded_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DeadlineExtensionReview(BaseModel):
    response_message: Optional[str] = None


# Escrow Schemas
class EscrowTransactionResponse(BaseModel):
    id: UUID
    bounty_id: UUID
    milestone_id: Optional[UUID] = None
    buyer_id: UUID
    artist_id: Optional[UUID] = None
    amount: float
    platform_fee: float
    status: str
    held_at: datetime
    released_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# Statistics Schema
class BountyStatsResponse(BaseModel):
    total_bounties: int
    open_bounties: int
    total_value: float
    average_budget: float
    completed_bounties: int
    active_artists: int


# List Response Schemas
class BountyListResponse(BaseModel):
    bounties: List[BountyResponse]
    total: int
    page: int
    limit: int


class ApplicationListResponse(BaseModel):
    applications: List[BountyApplicationResponse]
