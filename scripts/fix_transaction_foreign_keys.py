#!/usr/bin/env python3
"""
Fix foreign key columns in transactions table that are still INTEGER
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()


async def fix_transaction_fks():
    db_url = os.getenv('DATABASE_URL', 'postgresql+asyncpg://sdmodels:sdmodels@localhost:5432/sdmodels')
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    
    print("Fixing foreign key columns in transactions table...")
    conn = await asyncpg.connect(db_url)
    
    try:
        # Check current state
        print("\n1. Checking current column types...")
        columns = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'transactions'
            AND column_name IN ('buyer_id', 'seller_id', 'model_id')
        """)
        
        for col in columns:
            print(f"   {col['column_name']}: {col['data_type']}")
        
        # Add UUID columns
        print("\n2. Adding UUID columns...")
        await conn.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS uuid_buyer_id UUID")
        await conn.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS uuid_seller_id UUID")
        await conn.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS uuid_model_id UUID")
        
        # Populate UUID columns from referenced tables
        print("\n3. Checking if there's any data in transactions...")
        count = await conn.fetchval("SELECT COUNT(*) FROM transactions")
        print(f"   Found {count} rows")
        
        if count > 0:
            print("   ⚠️  WARNING: Transactions table has data. Cannot convert safely.")
            print("   Please backup and manually migrate the data.")
            return
        
        print("   ✅ No data - safe to convert")
        
        # Drop old foreign key constraints
        print("\n4. Dropping old foreign key constraints...")
        await conn.execute("ALTER TABLE transactions DROP CONSTRAINT IF EXISTS transactions_buyer_id_fkey")
        await conn.execute("ALTER TABLE transactions DROP CONSTRAINT IF EXISTS transactions_seller_id_fkey")
        await conn.execute("ALTER TABLE transactions DROP CONSTRAINT IF EXISTS transactions_model_id_fkey")
        
        # Drop old columns
        print("\n5. Dropping old INTEGER columns...")
        await conn.execute("ALTER TABLE transactions DROP COLUMN IF EXISTS buyer_id")
        await conn.execute("ALTER TABLE transactions DROP COLUMN IF EXISTS seller_id")
        await conn.execute("ALTER TABLE transactions DROP COLUMN IF EXISTS model_id")
        
        # Rename UUID columns
        print("\n6. Renaming UUID columns...")
        await conn.execute("ALTER TABLE transactions RENAME COLUMN uuid_buyer_id TO buyer_id")
        await conn.execute("ALTER TABLE transactions RENAME COLUMN uuid_seller_id TO seller_id")
        await conn.execute("ALTER TABLE transactions RENAME COLUMN uuid_model_id TO model_id")
        
        # Make columns NOT NULL
        print("\n7. Setting NOT NULL constraints...")
        await conn.execute("ALTER TABLE transactions ALTER COLUMN buyer_id SET NOT NULL")
        await conn.execute("ALTER TABLE transactions ALTER COLUMN seller_id SET NOT NULL")
        await conn.execute("ALTER TABLE transactions ALTER COLUMN model_id SET NOT NULL")
        
        # Recreate foreign key constraints
        print("\n8. Recreating foreign key constraints...")
        await conn.execute("""
            ALTER TABLE transactions
            ADD CONSTRAINT transactions_buyer_id_fkey
            FOREIGN KEY (buyer_id) REFERENCES users(id)
        """)
        
        await conn.execute("""
            ALTER TABLE transactions
            ADD CONSTRAINT transactions_seller_id_fkey
            FOREIGN KEY (seller_id) REFERENCES users(id)
        """)
        
        await conn.execute("""
            ALTER TABLE transactions
            ADD CONSTRAINT transactions_model_id_fkey
            FOREIGN KEY (model_id) REFERENCES models(id)
        """)
        
        print("\n✅ SUCCESS! Transactions table foreign keys converted to UUID")
        
        # Verify
        print("\n9. Verifying...")
        columns = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'transactions'
            AND column_name IN ('id', 'buyer_id', 'seller_id', 'model_id')
            ORDER BY column_name
        """)
        
        for col in columns:
            status = "✅" if col['data_type'] == 'uuid' else "❌"
            print(f"   {status} {col['column_name']}: {col['data_type']}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(fix_transaction_fks())
