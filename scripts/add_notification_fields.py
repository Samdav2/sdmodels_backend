"""
Add related_id and related_title fields to notifications table
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

async def add_notification_fields():
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Add related_id column
            await session.execute(text('''
                ALTER TABLE notifications 
                ADD COLUMN IF NOT EXISTS related_id UUID
            '''))
            
            # Add related_title column
            await session.execute(text('''
                ALTER TABLE notifications 
                ADD COLUMN IF NOT EXISTS related_title VARCHAR(255)
            '''))
            
            await session.commit()
            print("✅ Successfully added related_id and related_title columns to notifications table")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(add_notification_fields())
