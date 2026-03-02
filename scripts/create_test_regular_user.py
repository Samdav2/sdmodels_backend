#!/usr/bin/env python3
"""
Create a test regular user (buyer) for testing support messages
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, '.')

from app.models.user import User
from app.core.config import settings
from app.core.security import get_password_hash


async def create_test_user():
    """Create a test regular user"""
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    email = "testuser@example.com"
    username = "testuser"
    password = "testpass123"
    
    async with async_session() as session:
        # Check if user already exists
        from sqlmodel import select
        result = await session.execute(
            select(User).where(User.email == email)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"\n✅ Test user already exists:")
            print(f"   Email: {existing_user.email}")
            print(f"   Username: {existing_user.username}")
            print(f"   User Type: {existing_user.user_type}")
            print(f"   Password: testpass123")
            return
        
        # Create new user
        user = User(
            email=email,
            username=username,
            password_hash=get_password_hash(password),
            full_name="Test User",
            user_type="buyer",  # Regular user, NOT admin
            is_active=True,
            is_verified=True
        )
        
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        print(f"\n{'='*80}")
        print(f"✅ TEST USER CREATED SUCCESSFULLY")
        print(f"{'='*80}")
        print(f"Email:     {user.email}")
        print(f"Username:  {user.username}")
        print(f"Password:  testpass123")
        print(f"User Type: {user.user_type}")
        print(f"{'='*80}")
        print(f"\n📝 HOW TO TEST:")
        print(f"1. Logout from current admin account")
        print(f"2. Login with:")
        print(f"   Email: testuser@example.com")
        print(f"   Password: testpass123")
        print(f"3. Go to support and send a message")
        print(f"4. Message will appear on RIGHT side (user side)")
        print(f"5. API response will show: \"sender_type\": \"user\"")
        print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(create_test_user())
