from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.user import (
    UserCreate, LoginRequest, RegisterResponse, Token, 
    LoginResponse, UserResponse, GoogleAuthRequest, GoogleAuthResponse
)
from app.services.auth_service import AuthService
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session)
):
    """Register a new user account"""
    auth_service = AuthService(session)
    return await auth_service.register(user_data)


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    session: AsyncSession = Depends(get_session)
):
    """User login - returns tokens and user info including username"""
    auth_service = AuthService(session)
    result = await auth_service.login(login_data.email, login_data.password)
    
    # Get full user info
    from app.repositories.user_repository import UserRepository
    user_repo = UserRepository(session)
    user = await user_repo.get_by_email(login_data.email)
    
    return {
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "token_type": result["token_type"],
        "user": UserResponse.model_validate(user)
    }


@router.post("/admin/login")
async def admin_login(
    login_data: LoginRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Admin login endpoint
    
    Returns user info along with tokens to verify admin status on frontend.
    Frontend should check if user.user_type === 'admin' before allowing access.
    """
    auth_service = AuthService(session)
    result = await auth_service.login(login_data.email, login_data.password)
    
    # Get user info
    from app.repositories.user_repository import UserRepository
    user_repo = UserRepository(session)
    user = await user_repo.get_by_email(login_data.email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if user is admin
    if user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required. This account does not have admin privileges."
        )
    
    return {
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "token_type": result["token_type"],
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "user_type": user.user_type,
            "full_name": user.full_name,
            "avatar_url": user.avatar_url,
            "is_verified": user.is_verified,
            "is_active": user.is_active
        }
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information including username"""
    return UserResponse.model_validate(current_user)


@router.post("/forgot-password")
async def forgot_password(
    email: str,
    session: AsyncSession = Depends(get_session)
):
    """Request password reset"""
    # TODO: Implement password reset logic with email
    return {"message": "Password reset email sent"}


@router.post("/reset-password")
async def reset_password(
    token: str,
    new_password: str,
    session: AsyncSession = Depends(get_session)
):
    """Reset password with token"""
    # TODO: Implement password reset logic
    return {"message": "Password reset successful"}


@router.post("/verify-email")
async def verify_email(
    token: str,
    session: AsyncSession = Depends(get_session)
):
    """Verify email with token"""
    # TODO: Implement email verification logic
    return {"message": "Email verified successfully"}


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str = Body(..., embed=True),
    session: AsyncSession = Depends(get_session)
):
    """Refresh access token using refresh token"""
    from app.core.security import verify_token, create_access_token, create_refresh_token
    from app.repositories.user_repository import UserRepository
    from uuid import UUID
    
    # Verify refresh token
    try:
        payload = verify_token(refresh_token, "refresh")
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Verify user still exists and is active
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(UUID(user_id))
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Generate new tokens
        new_access_token = create_access_token({"sub": str(user.id)})
        new_refresh_token = create_refresh_token({"sub": str(user.id)})
        
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}"
        )


@router.post("/google", response_model=GoogleAuthResponse)
async def google_auth(
    auth_data: GoogleAuthRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Google OAuth authentication - handles both login and registration
    
    This endpoint:
    1. Verifies the Google token
    2. Checks if user exists by google_id or email
    3. If user exists: logs them in (returns is_new_user=False)
    4. If user doesn't exist: creates new account (returns is_new_user=True)
    
    Frontend should:
    - Send the Google ID token received from Google Sign-In
    - Specify user_type for new registrations (buyer, creator, seller)
    - Check is_new_user to show appropriate welcome message
    """
    from app.utils.google_oauth import verify_google_token
    from app.repositories.user_repository import UserRepository
    from app.core.security import create_access_token, create_refresh_token, get_password_hash
    from datetime import datetime
    import secrets
    
    # Verify Google token
    google_user = await verify_google_token(auth_data.token)
    
    user_repo = UserRepository(session)
    
    # Check if user exists by google_id
    user = await user_repo.get_by_google_id(google_user["google_id"])
    
    # If not found by google_id, check by email
    if not user:
        user = await user_repo.get_by_email(google_user["email"])
        
        # If user exists with this email but no google_id, link the account
        if user:
            user.google_id = google_user["google_id"]
            if not user.avatar_url and google_user["avatar_url"]:
                user.avatar_url = google_user["avatar_url"]
            user.last_login = datetime.utcnow()
            session.add(user)
            await session.commit()
            await session.refresh(user)
            is_new_user = False
        else:
            # Create new user
            # Generate username from email
            username_base = google_user["email"].split("@")[0]
            username = username_base
            counter = 1
            
            # Ensure username is unique
            while await user_repo.get_by_username(username):
                username = f"{username_base}{counter}"
                counter += 1
            
            # Create user with random password (won't be used for Google login)
            user = User(
                email=google_user["email"],
                username=username,
                password_hash=get_password_hash(secrets.token_urlsafe(32)),
                full_name=google_user["full_name"],
                user_type=auth_data.user_type,
                google_id=google_user["google_id"],
                avatar_url=google_user["avatar_url"],
                is_verified=True,  # Google accounts are pre-verified
                is_active=True,
                last_login=datetime.utcnow()
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            is_new_user = True
    else:
        # User exists, update last login
        user.last_login = datetime.utcnow()
        session.add(user)
        await session.commit()
        await session.refresh(user)
        is_new_user = False
    
    # Generate tokens
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user),
        "is_new_user": is_new_user
    }
