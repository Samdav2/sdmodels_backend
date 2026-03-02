from typing import Optional, List
from uuid import UUID
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserProfile, UserFollower
from app.core.security import get_password_hash


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, email: str, username: str, password: str, **kwargs) -> User:
        user = User(
            email=email,
            username=username,
            password_hash=get_password_hash(password),
            **kwargs
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    async def get_by_google_id(self, google_id: str) -> Optional[User]:
        """Get user by Google OAuth ID"""
        result = await self.session.execute(
            select(User).where(User.google_id == google_id)
        )
        return result.scalar_one_or_none()
    
    async def update(self, user_id: UUID, **kwargs) -> Optional[User]:
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def delete(self, user_id: UUID) -> bool:
        user = await self.get_by_id(user_id)
        if not user:
            return False
        
        await self.session.delete(user)
        await self.session.commit()
        return True
    
    async def get_profile(self, user_id: UUID) -> Optional[UserProfile]:
        result = await self.session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def create_or_update_profile(self, user_id: UUID, **kwargs) -> UserProfile:
        profile = await self.get_profile(user_id)
        
        if profile:
            for key, value in kwargs.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
        else:
            profile = UserProfile(user_id=user_id, **kwargs)
            self.session.add(profile)
        
        await self.session.commit()
        await self.session.refresh(profile)
        return profile
    
    async def follow_user(self, follower_id: UUID, following_id: UUID) -> UserFollower:
        follow = UserFollower(follower_id=follower_id, following_id=following_id)
        self.session.add(follow)
        await self.session.commit()
        await self.session.refresh(follow)
        return follow
    
    async def unfollow_user(self, follower_id: UUID, following_id: UUID) -> bool:
        result = await self.session.execute(
            select(UserFollower).where(
                UserFollower.follower_id == follower_id,
                UserFollower.following_id == following_id
            )
        )
        follow = result.scalar_one_or_none()
        
        if not follow:
            return False
        
        await self.session.delete(follow)
        await self.session.commit()
        return True
    
    async def get_followers(self, user_id: UUID, skip: int = 0, limit: int = 20) -> List[User]:
        result = await self.session.execute(
            select(User).join(UserFollower, User.id == UserFollower.follower_id)
            .where(UserFollower.following_id == user_id)
            .offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def get_following(self, user_id: UUID, skip: int = 0, limit: int = 20) -> List[User]:
        result = await self.session.execute(
            select(User).join(UserFollower, User.id == UserFollower.following_id)
            .where(UserFollower.follower_id == user_id)
            .offset(skip).limit(limit)
        )
        return result.scalars().all()
