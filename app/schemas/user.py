from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, validator


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str
    user_type: str = "buyer"
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    country: Optional[str] = None


class UserResponse(UserBase):
    id: UUID
    user_type: str
    is_verified: bool
    is_active: bool
    avatar_url: Optional[str]
    bio: Optional[str]
    created_at: datetime
    is_verified_creator: bool
    total_sales: float
    total_models: int
    rating: float
    
    class Config:
        from_attributes = True


# Auth Schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[UUID] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RegisterResponse(BaseModel):
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# Profile Schemas
class UserProfileUpdate(BaseModel):
    phone: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    website: Optional[str] = None
    twitter: Optional[str] = None
    instagram: Optional[str] = None
    portfolio_url: Optional[str] = None
    skills: Optional[List[str]] = None
    software: Optional[List[str]] = None


class UserProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    phone: Optional[str]
    country: Optional[str]
    city: Optional[str]
    website: Optional[str]
    twitter: Optional[str]
    instagram: Optional[str]
    portfolio_url: Optional[str]
    skills: List[str]
    software: List[str]
    
    class Config:
        from_attributes = True


# Password Reset
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class VerifyEmailRequest(BaseModel):
    token: str


# Google OAuth Schemas
class GoogleAuthRequest(BaseModel):
    token: str  # Google ID token from frontend
    user_type: str = "buyer"  # buyer, creator, seller
    
    @validator('user_type')
    def validate_user_type(cls, v):
        if v not in ["buyer", "creator", "seller"]:
            raise ValueError('user_type must be buyer, creator, or seller')
        return v


class GoogleAuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
    is_new_user: bool  # True if this was a registration, False if login
