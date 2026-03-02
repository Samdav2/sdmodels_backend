#!/usr/bin/env python3
"""
Setup script for payment methods and billing tables
"""
import asyncio
import asyncpg
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async def setup_tables():
    """Create payment_methods table and add tax fields to user_profiles"""
    
    # Parse DATABASE_URL
    # Format: postgresql+asyncpg://user:pass@host:port/dbname
    url = DATABASE_URL.replace("postgresql+asyncpg://", "")
    
    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "marketplace")
    )
    
    try:
        print("Creating payment_methods table...")
        
        # Create payment_methods table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS payment_methods (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                type VARCHAR(50) NOT NULL,
                is_primary BOOLEAN DEFAULT FALSE,
                
                -- PayPal
                paypal_email VARCHAR(255),
                
                -- Bank Account
                account_holder_name VARCHAR(255),
                account_number_last_four VARCHAR(4),
                routing_number VARCHAR(50),
                bank_name VARCHAR(255),
                
                -- Stripe
                stripe_account_id VARCHAR(255),
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("✓ payment_methods table created")
        
        # Add indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_payment_methods_user_id 
            ON payment_methods(user_id);
        """)
        print("✓ Indexes created")
        
        # Add tax fields to user_profiles table if they don't exist
        print("\nAdding tax fields to user_profiles table...")
        
        try:
            await conn.execute("""
                ALTER TABLE user_profiles 
                ADD COLUMN IF NOT EXISTS tax_id VARCHAR(50),
                ADD COLUMN IF NOT EXISTS business_name VARCHAR(255);
            """)
            print("✓ Tax fields added to user_profiles")
        except Exception as e:
            print(f"Note: Tax fields may already exist: {e}")
        
        print("\n✅ All tables and fields created successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(setup_tables())
