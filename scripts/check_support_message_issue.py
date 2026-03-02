#!/usr/bin/env python3
"""
Diagnostic script to check support message sender_type issue
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import select

sys.path.insert(0, '.')

from app.models.user import User
from app.models.support import SupportTicket, SupportMessage
from app.core.config import settings


async def diagnose_issue():
    """Check for users with wrong user_type and their messages"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        print("🔍 SUPPORT MESSAGE SENDER_TYPE DIAGNOSTIC\n")
        print("=" * 80)
        
        # Get all users
        result = await session.execute(select(User))
        users = result.scalars().all()
        
        print(f"\n📊 USER TYPES SUMMARY:")
        user_type_counts = {}
        for user in users:
            user_type_counts[user.user_type] = user_type_counts.get(user.user_type, 0) + 1
        
        for user_type, count in user_type_counts.items():
            print(f"   {user_type}: {count} users")
        
        # Check for potential issues
        print(f"\n⚠️  POTENTIAL ISSUES:")
        
        # Get all support messages
        msg_result = await session.execute(
            select(SupportMessage, User)
            .join(User, SupportMessage.sender_id == User.id)
            .order_by(SupportMessage.created_at.desc())
            .limit(20)
        )
        messages = msg_result.all()
        
        if not messages:
            print("   No support messages found in database")
            return
        
        print(f"\n📨 RECENT SUPPORT MESSAGES (last 20):")
        print(f"{'Sender Email':<30} {'User Type':<10} {'Sender Type':<12} {'Match':<8} {'Content Preview'}")
        print("-" * 100)
        
        mismatches = []
        for message, user in messages:
            expected_sender_type = "admin" if user.user_type == "admin" else "user"
            matches = "✅" if message.sender_type == expected_sender_type else "❌"
            content_preview = message.content[:40] + "..." if len(message.content) > 40 else message.content
            
            print(f"{user.email:<30} {user.user_type:<10} {message.sender_type:<12} {matches:<8} {content_preview}")
            
            if message.sender_type != expected_sender_type:
                mismatches.append({
                    'user': user,
                    'message': message,
                    'expected': expected_sender_type,
                    'actual': message.sender_type
                })
        
        if mismatches:
            print(f"\n❌ FOUND {len(mismatches)} MISMATCHED MESSAGES:")
            for item in mismatches:
                user = item['user']
                print(f"\n   User: {user.email} ({user.username})")
                print(f"   User Type: {user.user_type}")
                print(f"   Expected sender_type: {item['expected']}")
                print(f"   Actual sender_type: {item['actual']}")
                print(f"   Problem: User has user_type='{user.user_type}' but message has sender_type='{item['actual']}'")
                
                if user.user_type == "admin" and item['actual'] == "user":
                    print(f"   Fix: This is an admin, messages should be sender_type='admin' (already correct in code)")
                elif user.user_type in ["buyer", "creator"] and item['actual'] == "admin":
                    print(f"   Fix: Run: python scripts/fix_user_type.py {user.email} {user.user_type}")
        else:
            print(f"\n✅ All messages have correct sender_type!")
        
        # Check for users who might be incorrectly set as admin
        print(f"\n👥 ADMIN USERS:")
        admin_users = [u for u in users if u.user_type == "admin"]
        if admin_users:
            for admin in admin_users:
                print(f"   {admin.email} ({admin.username})")
                print(f"      Created: {admin.created_at}")
        else:
            print("   No admin users found")
        
        print(f"\n" + "=" * 80)
        print(f"\n💡 RECOMMENDATIONS:")
        print(f"   1. Check if any users are incorrectly marked as 'admin'")
        print(f"   2. Use: python scripts/fix_user_type.py --list (to see all users)")
        print(f"   3. Use: python scripts/fix_user_type.py <email> <buyer|creator> (to fix)")
        print(f"   4. After fixing, user should logout and login again")
        print(f"   5. New messages will have correct sender_type")


if __name__ == "__main__":
    asyncio.run(diagnose_issue())
