#!/usr/bin/env python3
"""
Verify that the bounty system is properly set up
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

async def verify_setup():
    """Verify bounty system setup"""
    print("=" * 60)
    print("Bounty System Verification")
    print("=" * 60)
    
    database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(database_url, echo=False)
    
    try:
        async with engine.connect() as conn:
            # Check tables exist
            print("\n1. Checking tables...")
            tables = ['bounties', 'bounty_applications', 'bounty_submissions', 'escrow_transactions']
            
            for table in tables:
                result = await conn.execute(
                    text(
                        "SELECT EXISTS (SELECT FROM information_schema.tables "
                        "WHERE table_schema = 'public' AND table_name = :table_name)"
                    ),
                    {"table_name": table}
                )
                exists = result.scalar()
                status = "✓" if exists else "✗"
                print(f"   {status} {table}")
            
            # Check indexes
            print("\n2. Checking indexes...")
            result = await conn.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE tablename IN ('bounties', 'bounty_applications', 'bounty_submissions', 'escrow_transactions') "
                    "ORDER BY tablename, indexname"
                )
            )
            indexes = result.fetchall()
            print(f"   ✓ Found {len(indexes)} indexes")
            
            # Check constraints
            print("\n3. Checking constraints...")
            result = await conn.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid IN ("
                    "  SELECT oid FROM pg_class "
                    "  WHERE relname IN ('bounties', 'bounty_applications', 'bounty_submissions', 'escrow_transactions')"
                    ")"
                )
            )
            constraints = result.fetchall()
            print(f"   ✓ Found {len(constraints)} constraints")
            
            # Check foreign keys
            print("\n4. Checking foreign keys...")
            result = await conn.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.table_constraints "
                    "WHERE constraint_type = 'FOREIGN KEY' "
                    "AND table_name IN ('bounties', 'bounty_applications', 'bounty_submissions', 'escrow_transactions')"
                )
            )
            fk_count = result.scalar()
            print(f"   ✓ Found {fk_count} foreign keys")
            
            print("\n" + "=" * 60)
            print("✅ Bounty system is properly set up!")
            print("=" * 60)
            print("\nNext steps:")
            print("1. Start server: uvicorn app.main:app --reload")
            print("2. Visit: http://localhost:8000/docs")
            print("3. Look for 'Bounties' section")
            print("=" * 60)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease run: python scripts/setup_bounty_tables.py")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(verify_setup())
