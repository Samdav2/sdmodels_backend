"""
Create payment tables for Paystack and NOWPayments integration
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

async def create_payment_tables():
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Create payments table (Paystack)
            await session.execute(text('''
                CREATE TABLE IF NOT EXISTS payments (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    wallet_id UUID REFERENCES wallets(id) ON DELETE SET NULL,
                    reference VARCHAR(255) UNIQUE NOT NULL,
                    amount DECIMAL(10, 2) NOT NULL,
                    currency VARCHAR(3) DEFAULT 'NGN',
                    status VARCHAR(20) DEFAULT 'pending',
                    payment_type VARCHAR(20) DEFAULT 'deposit',
                    channel VARCHAR(50),
                    paid_at TIMESTAMP,
                    payment_metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            '''))
            
            await session.execute(text('CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id)'))
            await session.execute(text('CREATE INDEX IF NOT EXISTS idx_payments_reference ON payments(reference)'))
            await session.execute(text('CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status)'))
            
            # Create crypto_payments table (NOWPayments)
            await session.execute(text('''
                CREATE TABLE IF NOT EXISTS crypto_payments (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    wallet_id UUID REFERENCES wallets(id) ON DELETE SET NULL,
                    payment_id VARCHAR(255) UNIQUE,
                    invoice_id VARCHAR(255) UNIQUE,
                    order_id VARCHAR(255) NOT NULL,
                    order_description TEXT,
                    price_amount DECIMAL(18, 8) NOT NULL,
                    price_currency VARCHAR(10) NOT NULL,
                    pay_amount DECIMAL(18, 8),
                    pay_currency VARCHAR(10),
                    actually_paid DECIMAL(18, 8),
                    payment_type VARCHAR(20) DEFAULT 'deposit',
                    pay_address TEXT,
                    payin_extra_id VARCHAR(255),
                    payout_id VARCHAR(255),
                    payout_address TEXT,
                    payout_extra_id VARCHAR(255),
                    outcome_amount DECIMAL(18, 8),
                    outcome_currency VARCHAR(10),
                    payment_status VARCHAR(20) DEFAULT 'waiting',
                    invoice_url TEXT,
                    ipn_callback_url TEXT,
                    is_fixed_rate BOOLEAN DEFAULT FALSE,
                    is_fee_paid_by_user BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            '''))
            
            await session.execute(text('CREATE INDEX IF NOT EXISTS idx_crypto_payments_user_id ON crypto_payments(user_id)'))
            await session.execute(text('CREATE INDEX IF NOT EXISTS idx_crypto_payments_payment_id ON crypto_payments(payment_id)'))
            await session.execute(text('CREATE INDEX IF NOT EXISTS idx_crypto_payments_invoice_id ON crypto_payments(invoice_id)'))
            await session.execute(text('CREATE INDEX IF NOT EXISTS idx_crypto_payments_order_id ON crypto_payments(order_id)'))
            await session.execute(text('CREATE INDEX IF NOT EXISTS idx_crypto_payments_payout_id ON crypto_payments(payout_id)'))
            await session.execute(text('CREATE INDEX IF NOT EXISTS idx_crypto_payments_status ON crypto_payments(payment_status)'))
            
            # Create withdrawal_requests table
            await session.execute(text('''
                CREATE TABLE IF NOT EXISTS withdrawal_requests (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    wallet_id UUID NOT NULL REFERENCES wallets(id) ON DELETE CASCADE,
                    amount DECIMAL(10, 2) NOT NULL,
                    currency VARCHAR(10) NOT NULL,
                    withdrawal_method VARCHAR(20) NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    payment_id UUID REFERENCES payments(id) ON DELETE SET NULL,
                    crypto_payment_id UUID REFERENCES crypto_payments(id) ON DELETE SET NULL,
                    bank_code VARCHAR(50),
                    account_number VARCHAR(50),
                    account_name VARCHAR(255),
                    crypto_address TEXT,
                    crypto_currency VARCHAR(10),
                    crypto_extra_id VARCHAR(255),
                    processed_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    failure_reason TEXT,
                    withdrawal_metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            '''))
            
            await session.execute(text('CREATE INDEX IF NOT EXISTS idx_withdrawal_requests_user_id ON withdrawal_requests(user_id)'))
            await session.execute(text('CREATE INDEX IF NOT EXISTS idx_withdrawal_requests_wallet_id ON withdrawal_requests(wallet_id)'))
            await session.execute(text('CREATE INDEX IF NOT EXISTS idx_withdrawal_requests_status ON withdrawal_requests(status)'))
            
            await session.commit()
            print("✅ Successfully created payment tables")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(create_payment_tables())
