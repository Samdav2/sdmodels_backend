from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    username: str = Field(unique=True, index=True)
    password_hash: str
    full_name: Optional[str] = None
    user_type: str = Field(default="buyer")  # buyer, creator, admin
    is_verified: bool = Field(default=False)
    is_active: bool = Field(default=True)
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
    # OAuth fields
    google_id: Optional[str] = None
    github_id: Optional[str] = None
    discord_id: Optional[str] = None
    
    # Creator specific
    is_verified_creator: bool = Field(default=False)
    total_sales: float = Field(default=0.0)
    total_models: int = Field(default=0)
    rating: float = Field(default=0.0)


class UserProfile(SQLModel, table=True):
    __tablename__ = "user_profiles"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", unique=True)
    phone: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    twitter: Optional[str] = None
    instagram: Optional[str] = None
    artstation: Optional[str] = None
    youtube: Optional[str] = None
    portfolio_url: Optional[str] = None
    skills: str = Field(default="[]")  # JSON array
    software: str = Field(default="[]")  # JSON array
    # Tax information
    tax_id: Optional[str] = None
    business_name: Optional[str] = None
    # Security settings
    two_factor_enabled: bool = Field(default=False)
    biometric_enabled: bool = Field(default=False)
    last_password_change: Optional[datetime] = None
    # Notification preferences
    email_notifications: bool = Field(default=True)
    push_notifications: bool = Field(default=False)
    alert_new_sales: bool = Field(default=True)
    alert_new_reviews: bool = Field(default=True)
    alert_new_followers: bool = Field(default=True)
    alert_messages: bool = Field(default=True)
    alert_platform_updates: bool = Field(default=False)
    alert_marketing: bool = Field(default=False)


class PaymentMethod(SQLModel, table=True):
    __tablename__ = "payment_methods"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    type: str  # paypal, bank_account, stripe
    is_primary: bool = Field(default=False)
    
    # PayPal
    paypal_email: Optional[str] = None
    
    # Bank Account
    account_holder_name: Optional[str] = None
    account_number_last_four: Optional[str] = None
    routing_number: Optional[str] = None
    bank_name: Optional[str] = None
    
    # Stripe
    stripe_account_id: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserFollower(SQLModel, table=True):
    __tablename__ = "user_followers"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    follower_id: UUID = Field(foreign_key="users.id")
    following_id: UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
