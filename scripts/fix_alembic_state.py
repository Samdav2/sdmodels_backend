#!/usr/bin/env python3
"""
Fix Alembic State - Mark migrations as applied
Since we already created tables with UUID using create_uuid_tables.py,
we need to tell Alembic that migrations 001 and 002 are already applied.
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def fix_alembic_state():
    """Mark migrations as applied in alembic_version table"""
    
    # Get database URL from environment
    db_url = os.getenv('DATABASE_URL', 'postgresql+asyncpg://sdmodels:sdmodels@localhost:5432/sdmodels')
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    
    print("Connecting to database...")
    conn = await asyncpg.connect(db_url)
    
    try:
        # Check if alembic_version table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'alembic_version'
            )
        """)
        
        if not table_exists:
            print("Creating alembic_version table...")
            await conn.execute("""
                CREATE TABLE alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
            """)
        
        # Check current version
        current_version = await conn.fetchval("SELECT version_num FROM alembic_version")
        
        if current_version:
            print(f"Current alembic version: {current_version}")
            
            # Update to latest version
            await conn.execute("UPDATE alembic_version SET version_num = '002'")
            print("✅ Updated alembic version to '002'")
        else:
            # Insert latest version
            await conn.execute("INSERT INTO alembic_version (version_num) VALUES ('002')")
            print("✅ Set alembic version to '002'")
        
        # Verify
        final_version = await conn.fetchval("SELECT version_num FROM alembic_version")
        print(f"\n✅ Alembic state fixed! Current version: {final_version}")
        print("\nThis means:")
        print("  - Migration 001 (create bounty tables) - MARKED AS APPLIED")
        print("  - Migration 002 (migrate to UUID) - MARKED AS APPLIED")
        print("\nYour database already has all tables with UUID, so this is correct.")
        
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(fix_alembic_state())
