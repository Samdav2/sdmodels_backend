"""
Create wallet system tables and migrate existing users
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import engine
from app.models.wallet import Wallet, WalletTransaction
from sqlmodel import SQLModel


async def create_wallet_tables():
    """Create wallet tables"""
    print("Creating wallet tables...")
    
    async with engine.begin() as conn:
        # Create wallets table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS wallets (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                available_balance DECIMAL(10, 2) DEFAULT 0.00 NOT NULL,
                held_balance DECIMAL(10, 2) DEFAULT 0.00 NOT NULL,
                total_deposited DECIMAL(10, 2) DEFAULT 0.00 NOT NULL,
                total_withdrawn DECIMAL(10, 2) DEFAULT 0.00 NOT NULL,
                total_earned DECIMAL(10, 2) DEFAULT 0.00 NOT NULL,
                currency VARCHAR(3) DEFAULT 'USD' NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT positive_available_balance CHECK (available_balance >= 0),
                CONSTRAINT positive_held_balance CHECK (held_balance >= 0)
            );
        """))
        print("✓ Created wallets table")
        
        # Create wallet_transactions table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS wallet_transactions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                wallet_id UUID NOT NULL REFERENCES wallets(id) ON DELETE CASCADE,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                transaction_type VARCHAR(50) NOT NULL,
                amount DECIMAL(10, 2) NOT NULL,
                balance_before DECIMAL(10, 2) NOT NULL,
                balance_after DECIMAL(10, 2) NOT NULL,
                status VARCHAR(20) DEFAULT 'completed' NOT NULL,
                description TEXT,
                reference_type VARCHAR(50),
                reference_id UUID,
                transaction_metadata JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT valid_transaction_type CHECK (
                    transaction_type IN (
                        'deposit', 'withdrawal', 'bounty_escrow', 'bounty_payment',
                        'bounty_refund', 'model_purchase', 'model_sale', 'platform_fee',
                        'milestone_escrow', 'milestone_payment'
                    )
                ),
                CONSTRAINT valid_status CHECK (status IN ('pending', 'completed', 'failed', 'cancelled'))
            );
        """))
        print("✓ Created wallet_transactions table")
        
        # Create indexes
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_wallets_user_id ON wallets(user_id);
        """))
        
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_wallet_transactions_wallet_id ON wallet_transactions(wallet_id);
        """))
        
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_wallet_transactions_user_id ON wallet_transactions(user_id);
        """))
        
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_wallet_transactions_type ON wallet_transactions(transaction_type);
        """))
        
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_wallet_transactions_created_at ON wallet_transactions(created_at DESC);
        """))
        
        print("✓ Created indexes")


async def create_wallets_for_existing_users():
    """Create wallets for all existing users"""
    print("\nCreating wallets for existing users...")
    
    async with engine.begin() as conn:
        # Get all users without wallets
        result = await conn.execute(text("""
            SELECT u.id, u.username
            FROM users u
            LEFT JOIN wallets w ON u.id = w.user_id
            WHERE w.id IS NULL
        """))
        
        users = result.fetchall()
        
        if not users:
            print("✓ All users already have wallets")
            return
        
        print(f"Found {len(users)} users without wallets")
        
        # Create wallet for each user
        for user_id, username in users:
            await conn.execute(text("""
                INSERT INTO wallets (user_id, available_balance, held_balance)
                VALUES (:user_id, 0.00, 0.00)
            """), {"user_id": user_id})
            print(f"  ✓ Created wallet for user: {username}")
        
        print(f"✓ Created {len(users)} wallets")


async def verify_wallet_system():
    """Verify wallet system is working"""
    print("\nVerifying wallet system...")
    
    async with engine.begin() as conn:
        # Check wallets table
        result = await conn.execute(text("SELECT COUNT(*) FROM wallets"))
        wallet_count = result.scalar()
        print(f"✓ Total wallets: {wallet_count}")
        
        # Check wallet_transactions table
        result = await conn.execute(text("SELECT COUNT(*) FROM wallet_transactions"))
        transaction_count = result.scalar()
        print(f"✓ Total transactions: {transaction_count}")
        
        # Check users without wallets
        result = await conn.execute(text("""
            SELECT COUNT(*)
            FROM users u
            LEFT JOIN wallets w ON u.id = w.user_id
            WHERE w.id IS NULL
        """))
        users_without_wallets = result.scalar()
        
        if users_without_wallets > 0:
            print(f"⚠ Warning: {users_without_wallets} users without wallets")
        else:
            print("✓ All users have wallets")


async def main():
    """Main function"""
    print("=" * 60)
    print("WALLET SYSTEM SETUP")
    print("=" * 60)
    
    try:
        # Create tables
        await create_wallet_tables()
        
        # Create wallets for existing users
        await create_wallets_for_existing_users()
        
        # Verify
        await verify_wallet_system()
        
        print("\n" + "=" * 60)
        print("✓ WALLET SYSTEM SETUP COMPLETE")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Restart your FastAPI server")
        print("2. Test wallet endpoints:")
        print("   - GET /api/v1/wallet/balance")
        print("   - POST /api/v1/wallet/deposit")
        print("   - GET /api/v1/wallet/transactions")
        print("3. Create bounties - funds will be held in escrow")
        print("4. Approve submissions - funds will be released to artists")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
