"""
Reset test user password
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import os
from dotenv import load_dotenv
from passlib.context import CryptContext

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def reset_password():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Hash the password
        hashed_password = pwd_context.hash("testpass123")
        
        # Update both test users
        await session.execute(text('''
            UPDATE users 
            SET password_hash = :password 
            WHERE email IN ('bloggers694@gmail.com', 'test_client_bounty@example.com')
        '''), {"password": hashed_password})
        
        await session.commit()
        print("✅ Password reset to 'testpass123' for both test users")

if __name__ == "__main__":
    asyncio.run(reset_password())
