from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.schemas.admin_user import (
    AdminLoginRequest, AdminLoginResponse,
    AdminUserCreate, AdminUserResponse, AdminUserUpdate
)
from app.services.admin_auth_service import AdminAuthService
from app.repositories.admin_user_repository import AdminUserRepository
from app.core.admin_dependencies import get_current_admin_user, require_superadmin
from app.models.admin_user import AdminUser

router = APIRouter()


@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(
    login_data: AdminLoginRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Admin login endpoint
    
    Completely separate from regular user login.
    Returns admin-specific tokens and admin user info.
    """
    auth_service = AdminAuthService(session)
    return await auth_service.login(login_data)


@router.get("/me", response_model=AdminUserResponse)
async def get_current_admin_info(
    current_admin: AdminUser = Depends(get_current_admin_user)
):
    """Get current admin user information"""
    return AdminUserResponse.model_validate(current_admin)


@router.post("/create", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_user(
    admin_data: AdminUserCreate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(require_superadmin)
):
    """
    Create a new admin user (Superadmin only)
    """
    admin_repo = AdminUserRepository(session)
    
    # Check if email already exists
    existing_admin = await admin_repo.get_by_email(admin_data.email)
    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username already exists
    existing_username = await admin_repo.get_by_username(admin_data.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    admin = await admin_repo.create(admin_data)
    return AdminUserResponse.model_validate(admin)


@router.get("/list", response_model=list[AdminUserResponse])
async def list_admin_users(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(require_superadmin)
):
    """
    List all admin users (Superadmin only)
    """
    admin_repo = AdminUserRepository(session)
    admins = await admin_repo.get_all(skip, limit)
    return [AdminUserResponse.model_validate(admin) for admin in admins]


@router.put("/{admin_id}", response_model=AdminUserResponse)
async def update_admin_user(
    admin_id: int,
    admin_data: AdminUserUpdate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(require_superadmin)
):
    """
    Update admin user (Superadmin only)
    """
    admin_repo = AdminUserRepository(session)
    
    admin = await admin_repo.update(admin_id, admin_data)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    
    return AdminUserResponse.model_validate(admin)


@router.delete("/{admin_id}")
async def delete_admin_user(
    admin_id: int,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(require_superadmin)
):
    """
    Delete admin user (Superadmin only)
    
    Cannot delete yourself
    """
    if admin_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    admin_repo = AdminUserRepository(session)
    success = await admin_repo.delete(admin_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    
    return {"message": "Admin user deleted successfully"}


@router.post("/{admin_id}/deactivate", response_model=AdminUserResponse)
async def deactivate_admin_user(
    admin_id: int,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(require_superadmin)
):
    """
    Deactivate admin user (Superadmin only)
    
    Cannot deactivate yourself
    """
    if admin_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    admin_repo = AdminUserRepository(session)
    admin = await admin_repo.deactivate(admin_id)
    
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    
    return AdminUserResponse.model_validate(admin)


@router.post("/logout")
async def admin_logout(
    current_admin: AdminUser = Depends(get_current_admin_user)
):
    """
    Admin logout
    
    Frontend should clear tokens from storage
    """
    return {"message": "Logged out successfully"}
