from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.user import UserResponse, UserUpdate
from app.repositories.user_repository import UserRepository
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user profile"""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_my_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update current user profile"""
    user_repo = UserRepository(session)
    updated_user = await user_repo.update(
        current_user.id,
        **user_data.model_dump(exclude_unset=True)
    )
    return updated_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_profile(
    user_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    """Get public user profile"""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.post("/{user_id}/follow")
async def follow_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Follow a user"""
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot follow yourself"
        )
    
    user_repo = UserRepository(session)
    await user_repo.follow_user(current_user.id, user_id)
    
    # Send new follower email
    try:
        from app.utils.email import send_new_follower_email
        from app.core.config import settings
        
        followed_user = await user_repo.get_by_id(user_id)
        if followed_user:
            await send_new_follower_email(
                user_email=followed_user.email,
                username=followed_user.username,
                follower_username=current_user.username,
                follower_bio=current_user.bio if hasattr(current_user, 'bio') else "No bio yet",
                follower_profile_url=f"{settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'}/users/{current_user.id}"
            )
    except Exception as e:
        print(f"Failed to send new follower email: {e}")
    
    return {"message": "User followed successfully"}


@router.delete("/{user_id}/follow")
async def unfollow_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Unfollow a user"""
    user_repo = UserRepository(session)
    success = await user_repo.unfollow_user(current_user.id, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Follow relationship not found"
        )
    
    return {"message": "User unfollowed successfully"}


@router.get("/{user_id}/followers")
async def get_user_followers(
    user_id: UUID,
    page: int = 1,
    limit: int = 20,
    session: AsyncSession = Depends(get_session)
):
    """Get user followers list"""
    skip = (page - 1) * limit
    user_repo = UserRepository(session)
    followers = await user_repo.get_followers(user_id, skip, limit)
    
    return {
        "followers": followers,
        "page": page,
        "limit": limit
    }


@router.get("/{user_id}/following")
async def get_user_following(
    user_id: UUID,
    page: int = 1,
    limit: int = 20,
    session: AsyncSession = Depends(get_session)
):
    """Get users being followed"""
    skip = (page - 1) * limit
    user_repo = UserRepository(session)
    following = await user_repo.get_following(user_id, skip, limit)
    
    return {
        "following": following,
        "page": page,
        "limit": limit
    }
