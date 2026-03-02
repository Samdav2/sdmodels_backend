"""
Add funds to test user's wallet for bounty testing
"""
import asyncio
import sys
from pathlib import Path
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.session import engine


async def add_funds_to_user(email: str, amount: Decimal):
    """Add funds to a user's wallet"""
    print(f"Adding ${amount} to user: {email}")
    
    async with engine.begin() as conn:
        # Get user
        result = await conn.execute(
            text("SELECT id, username FROM users WHERE email = :email"),
            {"email": email}
        )
        user = result.fetchone()
        
        if not user:
            print(f"❌ User not found: {email}")
            return False
        
        user_id, username = user
        print(f"✓ Found user: {username} (ID: {user_id})")
        
        # Get or create wallet
        result = await conn.execute(
            text("SELECT id, available_balance, held_balance FROM wallets WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        wallet = result.fetchone()
        
        if not wallet:
            print("  Creating wallet...")
            result = await conn.execute(
                text("""
                    INSERT INTO wallets (user_id, available_balance, held_balance)
                    VALUES (:user_id, 0.00, 0.00)
                    RETURNING id, available_balance, held_balance
                """),
                {"user_id": user_id}
            )
            wallet = result.fetchone()
            print("  ✓ Wallet created")
        
        wallet_id, current_available, current_held = wallet
        print(f"  Current balance: Available=${current_available}, Held=${current_held}")
        
        # Update wallet balance
        new_balance = Decimal(str(current_available)) + amount
        await conn.execute(
            text("""
                UPDATE wallets 
                SET available_balance = :new_balance,
                    total_deposited = total_deposited + :amount,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :wallet_id
            """),
            {
                "wallet_id": wallet_id,
                "new_balance": new_balance,
                "amount": amount
            }
        )
        print(f"  ✓ Updated balance to ${new_balance}")
        
        # Create transaction record
        await conn.execute(
            text("""
                INSERT INTO wallet_transactions (
                    id, wallet_id, user_id, transaction_type, amount,
                    balance_before, balance_after, status, description,
                    transaction_metadata, created_at
                )
                VALUES (
                    gen_random_uuid(), :wallet_id, :user_id, 'deposit', :amount,
                    :balance_before, :balance_after, 'completed',
                    'Test funds added for bounty testing',
                    '{"source": "test_script", "method": "manual"}',
                    CURRENT_TIMESTAMP
                )
            """),
            {
                "wallet_id": wallet_id,
                "user_id": user_id,
                "amount": amount,
                "balance_before": current_available,
                "balance_after": new_balance
            }
        )
        print("  ✓ Transaction recorded")
        
        return True


async def main():
    """Main function"""
    print("=" * 60)
    print("ADD FUNDS TO TEST USER")
    print("=" * 60)
    print()
    
    # Test user email (bounty client)
    test_user_email = "test_client_bounty@example.com"
    amount = Decimal("1000.00")
    
    try:
        success = await add_funds_to_user(test_user_email, amount)
        
        if success:
            print()
            print("=" * 60)
            print("✅ FUNDS ADDED SUCCESSFULLY")
            print("=" * 60)
            print()
            print(f"User: {test_user_email}")
            print(f"Amount added: ${amount}")
            print()
            print("You can now:")
            print("1. Login as this user")
            print("2. Check balance: GET /api/v1/wallet/balance")
            print("3. Create bounties with the available funds")
            print()
            print("Test credentials:")
            print(f"  Email: {test_user_email}")
            print("  Password: testpass123")
        else:
            print()
            print("=" * 60)
            print("❌ FAILED TO ADD FUNDS")
            print("=" * 60)
            print()
            print("Make sure:")
            print("1. The user exists in the database")
            print("2. The wallet tables are created")
            print("3. Run: python scripts/create_wallet_system.py")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
