from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.admin_user_repository import AdminUserRepository
from app.schemas.admin_user import AdminLoginRequest, AdminLoginResponse, AdminUserResponse
from app.core.security import verify_password, create_access_token, create_refresh_token
from app.core.config import settings


class AdminAuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.admin_repo = AdminUserRepository(db)
    
    async def login(self, login_data: AdminLoginRequest) -> AdminLoginResponse:
        """
        Admin login
        
        Returns tokens and admin user info
        """
        # Get admin by email
        admin = await self.admin_repo.get_by_email(login_data.email)
        
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Verify password
        if not verify_password(login_data.password, admin.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Check if admin is active
        if not admin.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin account is deactivated"
            )
        
        # Update last login
        await self.admin_repo.update_last_login(admin.id)
        
        # Create tokens with admin flag in payload
        access_token = create_access_token(
            data={"sub": str(admin.id), "is_admin": True}
        )
        refresh_token = create_refresh_token(
            data={"sub": str(admin.id), "is_admin": True}
        )
        
        # Prepare response
        admin_response = AdminUserResponse.model_validate(admin)
        
        return AdminLoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            admin=admin_response
        )
    
    async def get_current_admin(self, admin_id: int):
        """Get current admin user"""
        admin = await self.admin_repo.get_by_id(admin_id)
        
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admin not found"
            )
        
        if not admin.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin account is deactivated"
            )
        
        return admin
