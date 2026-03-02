#!/usr/bin/env python3
"""
Create a support ticket for a specific user
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import select
from uuid import UUID

sys.path.insert(0, '.')

from app.models.support import SupportTicket
from app.models.user import User
from app.core.config import settings


async def create_ticket_for_user(email: str):
    """Create a support ticket for a user"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Get user
        result = await session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"❌ User not found: {email}")
            return
        
        print(f"\n{'='*80}")
        print(f"Creating support ticket for: {user.email} ({user.username})")
        print(f"{'='*80}")
        
        # Create ticket
        ticket = SupportTicket(
            user_id=user.id,
            subject="Test Support Ticket",
            category="general",
            priority="medium",
            status="open"
        )
        
        session.add(ticket)
        await session.commit()
        await session.refresh(ticket)
        
        print(f"\n✅ Ticket created successfully!")
        print(f"\nTicket Details:")
        print(f"  ID:       {ticket.id}")
        print(f"  Subject:  {ticket.subject}")
        print(f"  Category: {ticket.category}")
        print(f"  Priority: {ticket.priority}")
        print(f"  Status:   {ticket.status}")
        print(f"  User ID:  {ticket.user_id}")
        print(f"\n{'='*80}")
        print(f"\n📝 Now you can send messages in this ticket:")
        print(f"   POST /api/v1/support/tickets/{ticket.id}/messages")
        print(f"   Authorization: Bearer <{user.username}'s token>")
        print(f"{'='*80}\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/create_ticket_for_user.py <email>")
        print("\nExamples:")
        print("  python scripts/create_ticket_for_user.py testuser@example.com")
        print("  python scripts/create_ticket_for_user.py bloggers694@gmail.com")
        sys.exit(1)
    
    email = sys.argv[1]
    asyncio.run(create_ticket_for_user(email))
