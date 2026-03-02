#!/usr/bin/env python3
"""
Initialize database with tables and create admin user
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

from app.core.config import settings
from app.models import *  # Import all models
from app.repositories.user_repository import UserRepository
from app.db.session import async_session


async def init_database():
    """Create all database tables"""
    print("Creating database tables...")
    
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    print("✅ Database tables created successfully!")
    
    await engine.dispose()


async def create_admin_user():
    """Create initial admin user"""
    print("\nCreating admin user...")
    
    async with async_session() as session:
        user_repo = UserRepository(session)
        
        # Check if admin exists
        existing_admin = await user_repo.get_by_email(settings.ADMIN_EMAIL)
        
        if existing_admin:
            print("⚠️  Admin user already exists!")
            return
        
        # Create admin user
        admin = await user_repo.create(
            email=settings.ADMIN_EMAIL,
            username="admin",
            password=settings.ADMIN_PASSWORD,
            full_name="System Administrator",
            user_type="admin"
        )
        
        print(f"✅ Admin user created: {admin.email}")


async def main():
    """Main initialization function"""
    print("🚀 Initializing SDModels Database...\n")
    
    try:
        await init_database()
        await create_admin_user()
        
        print("\n✨ Database initialization completed successfully!")
        print("\n📝 Next steps:")
        print("   1. Start the server: uvicorn app.main:app --reload")
        print("   2. Access API docs: http://localhost:8000/api/v1/docs")
        print(f"   3. Login as admin: {settings.ADMIN_EMAIL}")
        
    except Exception as e:
        print(f"\n❌ Error during initialization: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
