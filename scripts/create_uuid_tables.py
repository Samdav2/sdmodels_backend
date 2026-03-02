"""
Create fresh database tables with UUID primary keys

This script drops existing tables and recreates them with UUID.
ONLY use this in development! For production, use proper migration.
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

from app.core.config import settings
from app.models.user import User, UserProfile, PaymentMethod, UserFollower
from app.models.model import Model, ModelLike, ModelComment
from sqlmodel import SQLModel


async def recreate_tables():
    """Drop and recreate tables with UUID"""
    
    print("⚠️  WARNING: This will DROP ALL TABLES and recreate them!")
    print("   Only use this in development environment.")
    response = input("   Continue? (yes/no): ")
    
    if response.lower() != "yes":
        print("Aborted.")
        return
    
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        print("\n1. Enabling UUID extension...")
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        
        print("\n2. Dropping existing tables...")
        # Drop tables in correct order (respecting foreign keys)
        tables_to_drop = [
            'model_comments', 'model_likes', 'models',
            'user_followers', 'payment_methods', 'user_profiles', 'users',
            'alembic_version'
        ]
        
        for table in tables_to_drop:
            try:
                await conn.execute(text(f'DROP TABLE IF EXISTS {table} CASCADE'))
                print(f"   ✓ Dropped {table}")
            except Exception as e:
                print(f"   ⚠️  Could not drop {table}: {e}")
        
        print("\n3. Creating tables with UUID...")
        await conn.run_sync(SQLModel.metadata.create_all)
        
        print("\n✅ Tables recreated with UUID primary keys!")
        print("\n📝 Next steps:")
        print("   1. Create admin user: python scripts/create_admin_user.py")
        print("   2. Test registration: curl -X POST .../auth/register")
        print("   3. Verify UUIDs in responses")
    
    await engine.dispose()


if __name__ == "__main__":
    print("="*70)
    print("CREATE UUID TABLES")
    print("="*70)
    asyncio.run(recreate_tables())
