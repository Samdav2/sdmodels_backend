#!/usr/bin/env python3
"""Find tables that have UUID id but INTEGER foreign keys"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()


async def find_mixed_tables():
    db_url = os.getenv('DATABASE_URL', 'postgresql+asyncpg://sdmodels:sdmodels@localhost:5432/sdmodels')
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    
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
        
        print("Checking for tables with mixed ID types...")
        print("=" * 60)
        
        mixed_tables = []
        
        for table in tables:
            table_name = table['table_name']
            
            # Check if id is UUID
            id_type = await conn.fetchval("""
                SELECT data_type
                FROM information_schema.columns
                WHERE table_name = $1 AND column_name = 'id'
            """, table_name)
            
            if id_type == 'uuid':
                # Check for INTEGER foreign keys
                int_fks = await conn.fetch("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = $1
                    AND column_name LIKE '%_id'
                    AND column_name != 'id'
                    AND data_type IN ('integer', 'bigint')
                """, table_name)
                
                if int_fks:
                    mixed_tables.append((table_name, int_fks))
                    print(f"\n⚠️  {table_name}")
                    for fk in int_fks:
                        print(f"     - {fk['column_name']}: {fk['data_type']}")
        
        if not mixed_tables:
            print("\n✅ No tables with mixed ID types found!")
        else:
            print(f"\n\nFound {len(mixed_tables)} tables with mixed ID types")
            print("These need to be fixed!")
        
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(find_mixed_tables())
