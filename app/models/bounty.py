from typing import Optional, List
from datetime import datetime, date
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, JSON, Column
from sqlalchemy import CheckConstraint


class Bounty(SQLModel, table=True):
    __tablename__ = "bounties"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(max_length=255)
    description: str
    budget: float
    deadline: date
    category: str = Field(max_length=100)
    difficulty: str = Field(max_length=20)
    status: str = Field(default="open", max_length=50)
    requirements: str = Field(default="[]", sa_column=Column(JSON))
    
    # Milestone and revision settings
    has_milestones: bool = Field(default=False)
    max_revisions: int = Field(default=3)
    revision_count: int = Field(default=0)
    
    # Foreign keys
    poster_id: UUID = Field(foreign_key="users.id")
    claimed_by_id: Optional[UUID] = Field(default=None, foreign_key="users.id")
    
    # Timestamps
    claimed_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint("difficulty IN ('easy', 'medium', 'hard')", name="check_difficulty"),
        CheckConstraint("status IN ('open', 'claimed', 'in_progress', 'submitted', 'completed', 'cancelled')", name="check_status"),
    )


class BountyApplication(SQLModel, table=True):
    __tablename__ = "bounty_applications"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    bounty_id: UUID = Field(foreign_key="bounties.id")
    applicant_id: UUID = Field(foreign_key="users.id")
    proposal: str
    estimated_delivery: date
    portfolio_links: str = Field(default="[]", sa_column=Column(JSON))
    status: str = Field(default="pending", max_length=20)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="check_application_status"),
    )


class BountyMilestone(SQLModel, table=True):
    __tablename__ = "bounty_milestones"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    bounty_id: UUID = Field(foreign_key="bounties.id")
    title: str = Field(max_length=255)
    description: str
    amount: float
    deadline: date
    order: int = Field(default=1)
    status: str = Field(default="pending", max_length=50)
    
    # Timestamps
    started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'in_progress', 'submitted', 'completed', 'cancelled')", name="check_milestone_status"),
    )


class BountySubmission(SQLModel, table=True):
    __tablename__ = "bounty_submissions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    bounty_id: UUID = Field(foreign_key="bounties.id")
    milestone_id: Optional[UUID] = Field(default=None, foreign_key="bounty_milestones.id")
    artist_id: UUID = Field(foreign_key="users.id")
    
    # Submission type and file details
    submission_type: str = Field(default="upload", max_length=10)  # 'upload' or 'link'
    model_file_url: Optional[str] = Field(default=None, max_length=500)  # For uploaded files
    model_file_name: Optional[str] = Field(default=None, max_length=255)  # Original filename
    model_file_size: Optional[int] = None  # File size in bytes
    model_format: Optional[str] = Field(default=None, max_length=10)  # glb, fbx, obj, etc.
    external_model_url: Optional[str] = Field(default=None, max_length=500)  # For external links
    
    preview_images: str = Field(default="[]", sa_column=Column(JSON))
    notes: Optional[str] = None
    status: str = Field(default="pending", max_length=50)
    feedback: Optional[str] = None
    revision_number: int = Field(default=1)
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'approved', 'rejected', 'revision_requested')", name="check_submission_status"),
        CheckConstraint("submission_type IN ('upload', 'link')", name="check_submission_type"),
        # Ensure valid submission: either file upload or external link
        CheckConstraint(
            "(submission_type = 'upload' AND model_file_url IS NOT NULL) OR (submission_type = 'link' AND external_model_url IS NOT NULL)",
            name="check_valid_submission"
        ),
    )


class DeadlineExtensionRequest(SQLModel, table=True):
    __tablename__ = "deadline_extension_requests"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    bounty_id: UUID = Field(foreign_key="bounties.id")
    milestone_id: Optional[UUID] = Field(default=None, foreign_key="bounty_milestones.id")
    artist_id: UUID = Field(foreign_key="users.id")
    current_deadline: date
    requested_deadline: date
    reason: str
    status: str = Field(default="pending", max_length=20)
    response_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    responded_at: Optional[datetime] = None
    
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="check_extension_status"),
    )


class EscrowTransaction(SQLModel, table=True):
    __tablename__ = "escrow_transactions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    bounty_id: UUID = Field(foreign_key="bounties.id")
    milestone_id: Optional[UUID] = Field(default=None, foreign_key="bounty_milestones.id")
    buyer_id: UUID = Field(foreign_key="users.id")
    artist_id: Optional[UUID] = Field(default=None, foreign_key="users.id")
    amount: float
    platform_fee: float
    status: str = Field(default="held", max_length=50)
    held_at: datetime = Field(default_factory=datetime.utcnow)
    released_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint("status IN ('held', 'released', 'refunded')", name="check_escrow_status"),
    )
