#!/usr/bin/env python3
"""
Fix user type for a specific user
Usage: python scripts/fix_user_type.py <email> <buyer|creator|admin>
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import select

# Add parent directory to path
sys.path.insert(0, '.')

from app.models.user import User
from app.core.config import settings


async def fix_user_type(email: str, new_type: str):
    """Fix user type for a specific user"""
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"❌ User not found: {email}")
            return
        
        print(f"\n📋 User Information:")
        print(f"   Email: {user.email}")
        print(f"   Username: {user.username}")
        print(f"   Current user_type: {user.user_type}")
        
        if user.user_type == new_type:
            print(f"\n✅ User type is already '{new_type}'. No changes needed.")
            return
        
        print(f"\n🔄 Updating user_type from '{user.user_type}' to '{new_type}'...")
        user.user_type = new_type
        await session.commit()
        print(f"✅ Successfully updated user_type to: {new_type}")
        
        print(f"\n📝 Next Steps:")
        print(f"   1. User should logout and login again")
        print(f"   2. New messages will have correct sender_type")
        print(f"   3. Test by sending a support message")


async def list_users():
    """List all users with their types"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        result = await session.execute(
            select(User).order_by(User.created_at.desc())
        )
        users = result.scalars().all()
        
        print(f"\n📋 All Users ({len(users)} total):")
        print(f"{'Email':<30} {'Username':<20} {'Type':<10} {'Created'}")
        print("-" * 80)
        
        for user in users:
            created = user.created_at.strftime("%Y-%m-%d") if user.created_at else "N/A"
            print(f"{user.email:<30} {user.username:<20} {user.user_type:<10} {created}")


if __name__ == "__main__":
    if len(sys.argv) == 1 or sys.argv[1] == "--list":
        print("🔍 Listing all users...")
        asyncio.run(list_users())
    elif len(sys.argv) != 3:
        print("Usage:")
        print("  List all users:     python scripts/fix_user_type.py --list")
        print("  Fix user type:      python scripts/fix_user_type.py <email> <buyer|creator|admin>")
        print("\nExamples:")
        print("  python scripts/fix_user_type.py user@example.com buyer")
        print("  python scripts/fix_user_type.py creator@example.com creator")
        sys.exit(1)
    else:
        email = sys.argv[1]
        user_type = sys.argv[2]
        
        if user_type not in ["buyer", "creator", "admin"]:
            print("❌ Invalid user_type. Must be: buyer, creator, or admin")
            sys.exit(1)
        
        asyncio.run(fix_user_type(email, user_type))
