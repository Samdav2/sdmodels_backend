#!/usr/bin/env python3
"""
Verify all tables are using UUID for ID columns
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()


async def verify_uuid_tables():
    """Check that all tables use UUID for their ID columns"""
    
    db_url = os.getenv('DATABASE_URL', 'postgresql+asyncpg://sdmodels:sdmodels@localhost:5432/sdmodels')
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    
    print("Connecting to database...")
    conn = await asyncpg.connect(db_url)
    
    try:
        # Get all tables
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            AND table_name != 'alembic_version'
            ORDER BY table_name
        """)
        
        print(f"\n📊 Checking {len(tables)} tables for UUID usage...\n")
        
        uuid_tables = []
        int_tables = []
        
        for table in tables:
            table_name = table['table_name']
            
            # Check ID column type
            id_type = await conn.fetchval("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = $1 
                AND column_name = 'id'
            """, table_name)
            
            if id_type == 'uuid':
                uuid_tables.append(table_name)
                print(f"✅ {table_name:30s} - UUID")
            elif id_type:
                int_tables.append(table_name)
                print(f"❌ {table_name:30s} - {id_type.upper()}")
            else:
                print(f"⚠️  {table_name:30s} - NO ID COLUMN")
        
        print(f"\n{'='*60}")
        print(f"Summary:")
        print(f"  ✅ Tables using UUID: {len(uuid_tables)}")
        print(f"  ❌ Tables using INT:  {len(int_tables)}")
        
        if int_tables:
            print(f"\n⚠️  WARNING: The following tables still use INTEGER IDs:")
            for table in int_tables:
                print(f"     - {table}")
            print("\nThese tables need to be converted to UUID!")
        else:
            print(f"\n🎉 SUCCESS! All tables are using UUID for IDs!")
        
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(verify_uuid_tables())
