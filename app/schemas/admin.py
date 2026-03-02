from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class AdminStatsResponse(BaseModel):
    total_users: int
    total_models: int
    total_revenue: float
    active_users_today: int
    new_users_today: int
    pending_models: int
    pending_tickets: int


class UserUpdateAdmin(BaseModel):
    is_active: Optional[bool] = None
    is_verified_creator: Optional[bool] = None
    user_type: Optional[str] = None


class ModelApprovalRequest(BaseModel):
    reason: Optional[str] = None


class ModelRejectionRequest(BaseModel):
    reason: str


class ReportResolveRequest(BaseModel):
    action: str  # remove, dismiss, warn
    notes: Optional[str] = None


class AnnouncementCreate(BaseModel):
    title: str
    message: str
    target: str = "all"  # all, creators, buyers


class AdminLoginRequest(BaseModel):
    email: str
    password: str
    otp_code: str
