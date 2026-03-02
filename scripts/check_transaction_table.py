#!/usr/bin/env python3
"""Check the actual column types in the transactions table"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()


async def check_transaction_table():
    db_url = os.getenv('DATABASE_URL', 'postgresql+asyncpg://sdmodels:sdmodels@localhost:5432/sdmodels')
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    
    conn = await asyncpg.connect(db_url)
    
    try:
        # Get column types for transactions table
        columns = await conn.fetch("""
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns
            WHERE table_name = 'transactions'
            ORDER BY ordinal_position
        """)
        
        print("Transactions table columns:")
        print("=" * 60)
        for col in columns:
            print(f"{col['column_name']:20s} {col['data_type']:15s} ({col['udt_name']})")
        
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(check_transaction_table())
