#!/usr/bin/env python3
"""
Convert ALL database tables from INTEGER to UUID
This is a comprehensive migration that converts every table in the database.
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()


async def convert_all_to_uuid():
    """Convert all tables from INTEGER IDs to UUID"""
    
    db_url = os.getenv('DATABASE_URL', 'postgresql+asyncpg://sdmodels:sdmodels@localhost:5432/sdmodels')
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    
    print("🔄 Starting comprehensive UUID conversion...")
    print("⚠️  WARNING: This will modify ALL tables in the database!")
    print("\nConnecting to database...")
    
    conn = await asyncpg.connect(db_url)
    
    try:
        # Enable UUID extension
        await conn.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
        print("✅ UUID extension enabled")
        
        # Get all tables that still use INTEGER for id
        int_tables = await conn.fetch("""
            SELECT DISTINCT c.table_name
            FROM information_schema.columns c
            WHERE c.table_schema = 'public'
            AND c.column_name = 'id'
            AND c.data_type IN ('integer', 'bigint')
            AND c.table_name != 'alembic_version'
            ORDER BY c.table_name
        """)
        
        if not int_tables:
            print("\n✅ All tables already use UUID!")
            return
        
        print(f"\n📋 Found {len(int_tables)} tables to convert:")
        for table in int_tables:
            print(f"   - {table['table_name']}")
        
        print("\n🔄 Starting conversion process...")
        print("=" * 60)
        
        # Step 1: Add UUID columns to all tables
        print("\n📝 Step 1: Adding UUID columns...")
        for table in int_tables:
            table_name = table['table_name']
            print(f"   Adding uuid_id to {table_name}...")
            
            await conn.execute(f"""
                ALTER TABLE {table_name} 
                ADD COLUMN IF NOT EXISTS uuid_id UUID DEFAULT uuid_generate_v4()
            """)
            
            # Generate UUIDs for existing rows
            await conn.execute(f"""
                UPDATE {table_name} 
                SET uuid_id = uuid_generate_v4() 
                WHERE uuid_id IS NULL
            """)
        
        print("✅ UUID columns added to all tables")
        
        # Step 2: Add UUID foreign key columns
        print("\n📝 Step 2: Adding UUID foreign key columns...")
        
        # Get all foreign key relationships
        fk_relationships = await conn.fetch("""
            SELECT
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name,
                tc.constraint_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = 'public'
                AND kcu.column_name LIKE '%_id'
                AND kcu.column_name != 'uuid_id'
            ORDER BY tc.table_name, kcu.column_name
        """)
        
        for fk in fk_relationships:
            table_name = fk['table_name']
            column_name = fk['column_name']
            foreign_table = fk['foreign_table_name']
            uuid_column_name = f"uuid_{column_name}"
            
            print(f"   Adding {uuid_column_name} to {table_name}...")
            
            # Add UUID foreign key column
            await conn.execute(f"""
                ALTER TABLE {table_name}
                ADD COLUMN IF NOT EXISTS {uuid_column_name} UUID
            """)
            
            # Check if foreign table already uses UUID or still has uuid_id
            foreign_id_column = await conn.fetchval("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = $1
                AND column_name IN ('uuid_id', 'id')
                AND data_type = 'uuid'
                ORDER BY CASE WHEN column_name = 'id' THEN 1 ELSE 2 END
                LIMIT 1
            """, foreign_table)
            
            if foreign_id_column:
                # Populate UUID foreign key from referenced table
                await conn.execute(f"""
                    UPDATE {table_name} t
                    SET {uuid_column_name} = ref.{foreign_id_column}
                    FROM {foreign_table} ref
                    WHERE t.{column_name} = ref.id
                """)
            else:
                print(f"      ⚠️  Skipping {foreign_table} - no UUID column found yet")
        
        print("✅ UUID foreign key columns added")
        
        # Step 3: Drop old foreign key constraints
        print("\n📝 Step 3: Dropping old foreign key constraints...")
        for fk in fk_relationships:
            constraint_name = fk['constraint_name']
            table_name = fk['table_name']
            print(f"   Dropping {constraint_name} from {table_name}...")
            
            await conn.execute(f"""
                ALTER TABLE {table_name}
                DROP CONSTRAINT IF EXISTS {constraint_name}
            """)
        
        print("✅ Old foreign key constraints dropped")
        
        # Step 4: Drop old primary keys and rename UUID columns
        print("\n📝 Step 4: Converting primary keys to UUID...")
        for table in int_tables:
            table_name = table['table_name']
            print(f"   Converting {table_name}...")
            
            # Drop old primary key
            await conn.execute(f"""
                ALTER TABLE {table_name}
                DROP CONSTRAINT IF EXISTS {table_name}_pkey
            """)
            
            # Drop old id column
            await conn.execute(f"""
                ALTER TABLE {table_name}
                DROP COLUMN IF EXISTS id
            """)
            
            # Rename uuid_id to id
            await conn.execute(f"""
                ALTER TABLE {table_name}
                RENAME COLUMN uuid_id TO id
            """)
            
            # Make id NOT NULL
            await conn.execute(f"""
                ALTER TABLE {table_name}
                ALTER COLUMN id SET NOT NULL
            """)
            
            # Create new primary key
            await conn.execute(f"""
                ALTER TABLE {table_name}
                ADD PRIMARY KEY (id)
            """)
        
        print("✅ Primary keys converted to UUID")
        
        # Step 5: Rename UUID foreign key columns and drop old ones
        print("\n📝 Step 5: Converting foreign keys to UUID...")
        for fk in fk_relationships:
            table_name = fk['table_name']
            column_name = fk['column_name']
            uuid_column_name = f"uuid_{column_name}"
            
            print(f"   Converting {column_name} in {table_name}...")
            
            # Drop old foreign key column
            await conn.execute(f"""
                ALTER TABLE {table_name}
                DROP COLUMN IF EXISTS {column_name}
            """)
            
            # Rename UUID column
            await conn.execute(f"""
                ALTER TABLE {table_name}
                RENAME COLUMN {uuid_column_name} TO {column_name}
            """)
        
        print("✅ Foreign keys converted to UUID")
        
        # Step 6: Recreate foreign key constraints
        print("\n📝 Step 6: Recreating foreign key constraints...")
        for fk in fk_relationships:
            table_name = fk['table_name']
            column_name = fk['column_name']
            foreign_table = fk['foreign_table_name']
            constraint_name = fk['constraint_name']
            
            print(f"   Creating {constraint_name}...")
            
            await conn.execute(f"""
                ALTER TABLE {table_name}
                ADD CONSTRAINT {constraint_name}
                FOREIGN KEY ({column_name})
                REFERENCES {foreign_table} (id)
            """)
        
        print("✅ Foreign key constraints recreated")
        
        print("\n" + "=" * 60)
        print("🎉 SUCCESS! All tables converted to UUID!")
        print("=" * 60)
        
        # Verify
        remaining_int = await conn.fetch("""
            SELECT table_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND column_name = 'id'
            AND data_type IN ('integer', 'bigint')
            AND table_name != 'alembic_version'
        """)
        
        if remaining_int:
            print(f"\n⚠️  WARNING: {len(remaining_int)} tables still have INTEGER IDs:")
            for table in remaining_int:
                print(f"   - {table['table_name']}")
        else:
            print("\n✅ Verification: All tables now use UUID!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(convert_all_to_uuid())
