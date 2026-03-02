#!/usr/bin/env python3
"""
Check specific user by ID to see their user_type
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import select
from uuid import UUID

sys.path.insert(0, '.')

from app.models.user import User
from app.core.config import settings


async def check_user(user_id_str: str):
    """Check user by ID"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        user_id = UUID(user_id_str)
    except ValueError:
        print(f"❌ Invalid UUID: {user_id_str}")
        return
    
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"❌ User not found with ID: {user_id_str}")
            return
        
        print(f"\n{'='*80}")
        print(f"USER DETAILS FOR ID: {user_id_str}")
        print(f"{'='*80}")
        print(f"Email:        {user.email}")
        print(f"Username:     {user.username}")
        print(f"User Type:    {user.user_type}")
        print(f"Is Active:    {user.is_active}")
        print(f"Created:      {user.created_at}")
        print(f"{'='*80}")
        
        expected_sender_type = "admin" if user.user_type == "admin" else "user"
        print(f"\nExpected sender_type for messages: {expected_sender_type}")
        
        if user.user_type == "admin":
            print(f"✅ This user IS an admin - sender_type 'admin' is CORRECT")
        else:
            print(f"❌ This user is NOT an admin - sender_type should be 'user'")
            print(f"   Current user_type: {user.user_type}")
            print(f"   Fix: python scripts/fix_user_type.py {user.email} buyer")


if __name__ == "__main__":
    # The sender_id from your message
    sender_id = "8d4b15a3-14ad-4f6e-983d-696793734f43"
    
    print("Checking user who sent the message...")
    asyncio.run(check_user(sender_id))
