#!/usr/bin/env python3
"""
Integrate earnings systems: Connect Transaction table with Wallet system
This ensures all earnings are tracked consistently across both systems
"""
import asyncio
import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text, select
from app.db.session import engine
from app.models.transaction import Transaction
from app.models.wallet import Wallet, WalletTransaction
from app.repositories.wallet_repository import WalletRepository
from sqlalchemy.ext.asyncio import AsyncSession


async def integrate_earnings():
    """Integrate model sales earnings into wallet system"""
    print("=" * 60)
    print("INTEGRATING EARNINGS SYSTEMS")
    print("=" * 60)
    
    async with engine.begin() as conn:
        # Get all completed transactions that haven't been added to wallets
        print("\n1. Finding model sales transactions...")
        result = await conn.execute(text("""
            SELECT 
                t.id,
                t.seller_id,
                t.seller_amount,
                t.amount,
                t.platform_fee,
                t.model_id,
                t.transaction_id,
                t.created_at
            FROM transactions t
            WHERE t.payment_status = 'completed'
            ORDER BY t.created_at;
        """))
        
        transactions = result.fetchall()
        print(f"   Found {len(transactions)} completed model sales")
        
        if not transactions:
            print("   No transactions to process")
            return
        
        print("\n2. Processing each transaction...")
        processed = 0
        skipped = 0
        
        for tx in transactions:
            tx_id, seller_id, seller_amount, amount, platform_fee, model_id, transaction_id, created_at = tx
            
            # Check if this transaction already exists in wallet_transactions
            check_result = await conn.execute(text("""
                SELECT COUNT(*) FROM wallet_transactions
                WHERE reference_type = 'model_sale'
                AND reference_id = :model_id
                AND user_id = :seller_id
                AND ABS(amount - :seller_amount) < 0.01;
            """), {
                "model_id": model_id,
                "seller_id": seller_id,
                "seller_amount": float(seller_amount)
            })
            
            exists = check_result.scalar()
            
            if exists > 0:
                skipped += 1
                continue
            
            # Get or create wallet for seller
            wallet_result = await conn.execute(text("""
                SELECT id, available_balance, total_earned
                FROM wallets
                WHERE user_id = :user_id;
            """), {"user_id": seller_id})
            
            wallet = wallet_result.first()
            
            if not wallet:
                # Create wallet
                await conn.execute(text("""
                    INSERT INTO wallets (user_id, available_balance, held_balance, total_earned, currency)
                    VALUES (:user_id, :amount, 0, :amount, 'USD');
                """), {
                    "user_id": seller_id,
                    "amount": float(seller_amount)
                })
                
                # Get the created wallet
                wallet_result = await conn.execute(text("""
                    SELECT id, available_balance, total_earned
                    FROM wallets
                    WHERE user_id = :user_id;
                """), {"user_id": seller_id})
                wallet = wallet_result.first()
            else:
                # Update existing wallet
                wallet_id, current_balance, current_earned = wallet
                new_balance = float(current_balance) + float(seller_amount)
                new_earned = float(current_earned) + float(seller_amount)
                
                await conn.execute(text("""
                    UPDATE wallets
                    SET available_balance = :new_balance,
                        total_earned = :new_earned,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :wallet_id;
                """), {
                    "wallet_id": wallet_id,
                    "new_balance": new_balance,
                    "new_earned": new_earned
                })
            
            # Get wallet again to get current balance
            wallet_result = await conn.execute(text("""
                SELECT id, available_balance
                FROM wallets
                WHERE user_id = :user_id;
            """), {"user_id": seller_id})
            wallet_id, current_balance = wallet_result.first()
            
            # Create wallet transaction record
            balance_before = float(current_balance) - float(seller_amount)
            
            await conn.execute(text("""
                INSERT INTO wallet_transactions (
                    wallet_id, user_id, transaction_type, amount,
                    balance_before, balance_after, status, description,
                    reference_type, reference_id, transaction_metadata, created_at
                )
                VALUES (
                    :wallet_id, :user_id, 'model_sale', :amount,
                    :balance_before, :balance_after, 'completed', :description,
                    'model_sale', :model_id, '{}', :created_at
                );
            """), {
                "wallet_id": wallet_id,
                "user_id": seller_id,
                "amount": float(seller_amount),
                "balance_before": balance_before,
                "balance_after": float(current_balance),
                "description": f"Model sale earnings (Transaction: {transaction_id})",
                "model_id": model_id,
                "created_at": created_at
            })
            
            processed += 1
            
            if processed % 10 == 0:
                print(f"   Processed {processed}/{len(transactions)} transactions...")
        
        print(f"\n✓ Processed {processed} transactions")
        print(f"✓ Skipped {skipped} already integrated transactions")
    
    print("\n3. Verifying integration...")
    async with engine.begin() as conn:
        # Check wallet totals
        result = await conn.execute(text("""
            SELECT 
                COUNT(*) as wallet_count,
                SUM(total_earned) as total_earnings,
                SUM(available_balance) as total_available
            FROM wallets;
        """))
        
        wallet_stats = result.first()
        print(f"   Wallets: {wallet_stats[0]}")
        print(f"   Total Earned: ${wallet_stats[1] or 0:.2f}")
        print(f"   Total Available: ${wallet_stats[2] or 0:.2f}")
        
        # Check wallet transactions
        result = await conn.execute(text("""
            SELECT COUNT(*) FROM wallet_transactions
            WHERE transaction_type = 'model_sale';
        """))
        
        tx_count = result.scalar()
        print(f"   Model Sale Transactions: {tx_count}")
    
    print("\n" + "=" * 60)
    print("✓ INTEGRATION COMPLETE")
    print("=" * 60)
    print("\nNext Steps:")
    print("1. Update model purchase flow to use wallet system")
    print("2. Ensure all future sales update both systems")
    print("3. Consider deprecating old Transaction table")


if __name__ == "__main__":
    asyncio.run(integrate_earnings())
