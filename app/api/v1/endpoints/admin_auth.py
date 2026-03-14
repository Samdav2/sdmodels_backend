from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.user import LoginRequest

router = APIRouter()


@router.post("/login")
async def admin_login(
    login_data: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Admin login endpoint (mounted at /api/v1/admin/auth/login).

    Returns tokens and user info. Raises 403 if the account is not an admin.
    """
    from app.services.auth_service import AuthService
    from app.repositories.user_repository import UserRepository

    auth_service = AuthService(session)
    result = await auth_service.login(login_data.email, login_data.password)

    user_repo = UserRepository(session)
    user = await user_repo.get_by_email(login_data.email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required. This account does not have admin privileges.",
        )

    return {
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "token_type": result["token_type"],
        "user": {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "user_type": user.user_type,
            "full_name": user.full_name,
            "avatar_url": user.avatar_url,
            "is_verified": user.is_verified,
            "is_active": user.is_active,
        },
    }


@router.post("/logout")
async def admin_logout():
    """Admin logout — client should discard tokens."""
    return {"message": "Logged out successfully"}
