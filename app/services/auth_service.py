from typing import Optional
from uuid import UUID
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository
from app.core.security import verify_password, create_access_token, create_refresh_token
from app.schemas.user import UserCreate, UserResponse, Token
from app.models.user import User


class AuthService:
    def __init__(self, session: AsyncSession):
        self.user_repo = UserRepository(session)
    
    async def register(self, user_data: UserCreate) -> dict:
        # Check if email exists
        existing_user = await self.user_repo.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if username exists
        existing_username = await self.user_repo.get_by_username(user_data.username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # Create user
        user = await self.user_repo.create(
            email=user_data.email,
            username=user_data.username,
            password=user_data.password,
            full_name=user_data.full_name,
            user_type=user_data.user_type
        )
        
        # Generate tokens
        access_token = create_access_token({"sub": str(user.id)})
        refresh_token = create_refresh_token({"sub": str(user.id)})
        
        # Send welcome email
        try:
            from app.utils.email import send_welcome_email, send_email_verification_email
            from app.core.config import settings
            import random
            
            verification_token = create_access_token({"sub": str(user.id), "type": "verify"})
            verification_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            
            # Send welcome email
            await send_welcome_email(
                user_email=user.email,
                username=user.username,
                verify_url=f"{settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'}/verify-email/{verification_token}"
            )
            
            # Also send verification email with code
            await send_email_verification_email(
                user_email=user.email,
                username=user.username,
                verify_url=f"{settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'}/verify-email/{verification_token}",
                verification_code=verification_code
            )
        except Exception as e:
            print(f"Failed to send welcome email: {e}")
        
        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    async def login(self, email: str, password: str) -> dict:
        # Get user by email
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Verify password
        if not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )
        
        # Update last login
        await self.user_repo.update(user.id, last_login=datetime.utcnow())
        
        # Generate tokens
        access_token = create_access_token({"sub": str(user.id)})
        refresh_token = create_refresh_token({"sub": str(user.id)})
        
        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    async def get_current_user(self, user_id: UUID) -> Optional[User]:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user

    
    async def request_password_reset(self, email: str) -> dict:
        """Request password reset"""
        from app.utils.email import send_password_reset_email
        from app.core.config import settings
        
        user = await self.user_repo.get_by_email(email)
        if not user:
            # Don't reveal if email exists
            return {"message": "If email exists, reset link has been sent"}
        
        # Generate reset token
        reset_token = create_access_token({"sub": str(user.id), "type": "reset"})
        
        # Send reset email
        try:
            await send_password_reset_email(
                user_email=user.email,
                username=user.username,
                reset_url=f"{settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'}/reset-password/{reset_token}"
            )
        except Exception as e:
            print(f"Failed to send password reset email: {e}")
        
        return {"message": "If email exists, reset link has been sent"}
