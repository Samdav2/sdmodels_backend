"""
Fix metadata column names in payment tables (reserved keyword issue)
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

async def fix_metadata_columns():
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Rename metadata to payment_metadata in payments table
            await session.execute(text('''
                ALTER TABLE payments 
                RENAME COLUMN metadata TO payment_metadata
            '''))
            print("✅ Renamed payments.metadata to payment_metadata")
            
            # Rename metadata to withdrawal_metadata in withdrawal_requests table
            await session.execute(text('''
                ALTER TABLE withdrawal_requests 
                RENAME COLUMN metadata TO withdrawal_metadata
            '''))
            print("✅ Renamed withdrawal_requests.metadata to withdrawal_metadata")
            
            await session.commit()
            print("✅ Successfully fixed metadata column names")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(fix_metadata_columns())
