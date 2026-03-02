from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field


class AdminUser(SQLModel, table=True):
    __tablename__ = "admin_users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    username: str = Field(unique=True, index=True)
    password_hash: str
    full_name: Optional[str] = None
    role: str = Field(default="admin")  # admin, superadmin, moderator
    is_active: bool = Field(default=True)
    avatar_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
    # Permissions
    can_manage_users: bool = Field(default=True)
    can_manage_bounties: bool = Field(default=True)
    can_manage_content: bool = Field(default=True)
    can_manage_settings: bool = Field(default=True)
    can_view_analytics: bool = Field(default=True)
