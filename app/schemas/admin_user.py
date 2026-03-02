from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class AdminUserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = None


class AdminUserCreate(AdminUserBase):
    password: str = Field(..., min_length=8)


class AdminUserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None
    can_manage_users: Optional[bool] = None
    can_manage_bounties: Optional[bool] = None
    can_manage_content: Optional[bool] = None
    can_manage_settings: Optional[bool] = None
    can_view_analytics: Optional[bool] = None


class AdminUserResponse(AdminUserBase):
    id: UUID
    role: str
    is_active: bool
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    can_manage_users: bool
    can_manage_bounties: bool
    can_manage_content: bool
    can_manage_settings: bool
    can_view_analytics: bool
    
    class Config:
        from_attributes = True


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    admin: AdminUserResponse
