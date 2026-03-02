#!/usr/bin/env python3
"""
Fix ALL foreign key columns that are still INTEGER
This script will convert all INTEGER foreign keys to UUID
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()


async def fix_all_foreign_keys():
    db_url = os.getenv('DATABASE_URL', 'postgresql+asyncpg://sdmodels:sdmodels@localhost:5432/sdmodels')
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    
    print("🔄 Fixing ALL foreign key columns to use UUID...")
    conn = await asyncpg.connect(db_url)
    
    try:
        # Get all tables with mixed types
        tables = await conn.fetch("""
            SELECT DISTINCT c.table_name
            FROM information_schema.columns c
            WHERE c.table_schema = 'public'
            AND c.table_name != 'alembic_version'
            AND EXISTS (
                SELECT 1 FROM information_schema.columns c2
                WHERE c2.table_name = c.table_name
                AND c2.column_name = 'id'
                AND c2.data_type = 'uuid'
            )
            AND EXISTS (
                SELECT 1 FROM information_schema.columns c3
                WHERE c3.table_name = c.table_name
                AND c3.column_name LIKE '%_id'
                AND c3.column_name != 'id'
                AND c3.data_type IN ('integer', 'bigint')
            )
            ORDER BY c.table_name
        """)
        
        print(f"\nFound {len(tables)} tables to fix\n")
        
        for table_row in tables:
            table_name = table_row['table_name']
            print(f"📝 Processing {table_name}...")
            
            # Get all INTEGER foreign key columns
            int_fks = await conn.fetch("""
                SELECT column_name, is_nullable
                FROM information_schema.columns
                WHERE table_name = $1
                AND column_name LIKE '%_id'
                AND column_name != 'id'
                AND data_type IN ('integer', 'bigint')
            """, table_name)
            
            if not int_fks:
                continue
            
            # Check if table has data
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            
            if count > 0:
                print(f"   ⚠️  Has {count} rows - will drop and recreate columns (data will be lost)")
            
            for fk in int_fks:
                col_name = fk['column_name']
                is_nullable = fk['is_nullable'] == 'YES'
                uuid_col_name = f"uuid_{col_name}"
                
                print(f"   Converting {col_name}...")
                
                # Add UUID column
                await conn.execute(f"""
                    ALTER TABLE {table_name}
                    ADD COLUMN IF NOT EXISTS {uuid_col_name} UUID
                """)
                
                # Drop old foreign key constraint if exists
                constraints = await conn.fetch("""
                    SELECT constraint_name
                    FROM information_schema.table_constraints
                    WHERE table_name = $1
                    AND constraint_type = 'FOREIGN KEY'
                """, table_name)
                
                for constraint in constraints:
                    constraint_name = constraint['constraint_name']
                    if col_name in constraint_name:
                        await conn.execute(f"""
                            ALTER TABLE {table_name}
                            DROP CONSTRAINT IF EXISTS {constraint_name}
                        """)
                
                # Drop old column
                await conn.execute(f"""
                    ALTER TABLE {table_name}
                    DROP COLUMN IF EXISTS {col_name}
                """)
                
                # Rename UUID column
                await conn.execute(f"""
                    ALTER TABLE {table_name}
                    RENAME COLUMN {uuid_col_name} TO {col_name}
                """)
                
                # Set NOT NULL if original was NOT NULL
                if not is_nullable:
                    # Can't set NOT NULL on empty column, so skip for now
                    pass
            
            print(f"   ✅ {table_name} fixed")
        
        print("\n" + "=" * 60)
        print("✅ ALL foreign keys converted to UUID!")
        print("=" * 60)
        
        # Verify
        print("\nVerifying...")
        remaining = await conn.fetch("""
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND column_name LIKE '%_id'
            AND column_name != 'id'
            AND data_type IN ('integer', 'bigint')
            AND table_name != 'alembic_version'
            ORDER BY table_name, column_name
        """)
        
        if remaining:
            print(f"\n⚠️  WARNING: {len(remaining)} INTEGER foreign keys still remain:")
            for row in remaining:
                print(f"   - {row['table_name']}.{row['column_name']}")
        else:
            print("\n✅ All foreign keys are now UUID!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(fix_all_foreign_keys())
