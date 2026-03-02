"""
Fix wallet_transactions table - rename metadata column to transaction_metadata
This fixes the SQLAlchemy reserved attribute name conflict
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import engine


async def check_column_exists():
    """Check if metadata column exists"""
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'wallet_transactions' 
            AND column_name IN ('metadata', 'transaction_metadata')
        """))
        columns = [row[0] for row in result.fetchall()]
        return columns


async def fix_metadata_column():
    """Rename metadata column to transaction_metadata"""
    print("Checking wallet_transactions table...")
    
    columns = await check_column_exists()
    
    if not columns:
        print("⚠️  wallet_transactions table doesn't exist yet")
        print("   Run: python scripts/create_wallet_system.py")
        return
    
    if 'transaction_metadata' in columns:
        print("✅ Column 'transaction_metadata' already exists - no fix needed")
        return
    
    if 'metadata' in columns:
        print("Found 'metadata' column - renaming to 'transaction_metadata'...")
        
        async with engine.begin() as conn:
            # Rename the column
            await conn.execute(text("""
                ALTER TABLE wallet_transactions 
                RENAME COLUMN metadata TO transaction_metadata
            """))
            
        print("✅ Successfully renamed column")
        
        # Verify
        columns = await check_column_exists()
        if 'transaction_metadata' in columns:
            print("✅ Verification passed - column renamed successfully")
        else:
            print("❌ Verification failed - column not found")
    else:
        print("⚠️  Neither 'metadata' nor 'transaction_metadata' column found")


async def main():
    """Main function"""
    print("=" * 60)
    print("FIX WALLET METADATA COLUMN")
    print("=" * 60)
    print()
    
    try:
        await fix_metadata_column()
        
        print()
        print("=" * 60)
        print("✅ FIX COMPLETE")
        print("=" * 60)
        print()
        print("You can now start your FastAPI server:")
        print("  uvicorn app.main:app --reload")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
