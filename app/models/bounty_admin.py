from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, JSON, Column
from sqlalchemy import CheckConstraint


class BountyDispute(SQLModel, table=True):
    __tablename__ = "bounty_disputes"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    bounty_id: UUID = Field(foreign_key="bounties.id")
    raised_by_id: UUID = Field(foreign_key="users.id")
    raised_by_role: str = Field(max_length=20)
    reason: str
    status: str = Field(default="open", max_length=50)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolved_by_admin_id: Optional[int] = Field(default=None, foreign_key="users.id")
    
    __table_args__ = (
        CheckConstraint("raised_by_role IN ('buyer', 'artist')", name="check_raised_by_role"),
        CheckConstraint("status IN ('open', 'resolved', 'escalated')", name="check_dispute_status"),
    )


class BountyDisputeResolution(SQLModel, table=True):
    __tablename__ = "bounty_dispute_resolutions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    dispute_id: UUID = Field(foreign_key="bounty_disputes.id")
    bounty_id: UUID = Field(foreign_key="bounties.id")
    admin_id: UUID = Field(foreign_key="users.id")
    winner: str = Field(max_length=20)
    refund_percentage: Optional[int] = None
    notes: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint("winner IN ('buyer', 'artist')", name="check_winner"),
        CheckConstraint("refund_percentage >= 0 AND refund_percentage <= 100", name="check_refund_percentage"),
    )


class BountySettings(SQLModel, table=True):
    __tablename__ = "bounty_settings"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    min_bounty_amount: float = Field(default=10.00)
    max_bounty_amount: float = Field(default=10000.00)
    platform_fee_percentage: float = Field(default=7.50)
    escrow_hold_days: int = Field(default=3)
    auto_approve_after_days: int = Field(default=14)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by_admin_id: Optional[int] = Field(default=None, foreign_key="users.id")


class UserBountyBan(SQLModel, table=True):
    __tablename__ = "user_bounty_bans"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", unique=True)
    banned_by_admin_id: UUID = Field(foreign_key="users.id")
    reason: str
    banned_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    is_permanent: bool = Field(default=False)


class AdminBountyAction(SQLModel, table=True):
    __tablename__ = "admin_bounty_actions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    admin_id: UUID = Field(foreign_key="users.id")
    bounty_id: Optional[int] = Field(default=None, foreign_key="bounties.id")
    action_type: str = Field(max_length=100)
    details: str = Field(default="{}", sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
