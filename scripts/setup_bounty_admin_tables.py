#!/usr/bin/env python3
"""
Script to set up admin bounty tables in the database.
"""
import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

async def create_admin_tables(engine):
    """Create admin bounty tables"""
    print("Creating admin bounty tables...")
    async with engine.begin() as conn:
        # Create bounty_disputes table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS bounty_disputes (
                id SERIAL PRIMARY KEY,
                bounty_id INTEGER NOT NULL REFERENCES bounties(id),
                raised_by_id INTEGER NOT NULL REFERENCES users(id),
                raised_by_role VARCHAR(20) NOT NULL CHECK (raised_by_role IN ('buyer', 'artist')),
                reason TEXT NOT NULL,
                status VARCHAR(50) DEFAULT 'open' NOT NULL CHECK (status IN ('open', 'resolved', 'escalated')),
                created_at TIMESTAMP DEFAULT NOW() NOT NULL,
                resolved_at TIMESTAMP,
                resolved_by_admin_id INTEGER REFERENCES users(id)
            )
        """))
        
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_bounty_disputes_id ON bounty_disputes(id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_bounty_disputes_bounty_id ON bounty_disputes(bounty_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_bounty_disputes_status ON bounty_disputes(status)"))
        
        # Create bounty_dispute_resolutions table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS bounty_dispute_resolutions (
                id SERIAL PRIMARY KEY,
                dispute_id INTEGER NOT NULL REFERENCES bounty_disputes(id),
                bounty_id INTEGER NOT NULL REFERENCES bounties(id),
                admin_id INTEGER NOT NULL REFERENCES users(id),
                winner VARCHAR(20) NOT NULL CHECK (winner IN ('buyer', 'artist')),
                refund_percentage INTEGER CHECK (refund_percentage >= 0 AND refund_percentage <= 100),
                notes TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW() NOT NULL
            )
        """))
        
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_bounty_dispute_resolutions_id ON bounty_dispute_resolutions(id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_bounty_dispute_resolutions_dispute_id ON bounty_dispute_resolutions(dispute_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_bounty_dispute_resolutions_bounty_id ON bounty_dispute_resolutions(bounty_id)"))
        
        # Create bounty_settings table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS bounty_settings (
                id SERIAL PRIMARY KEY,
                min_bounty_amount FLOAT DEFAULT 10.00 NOT NULL,
                max_bounty_amount FLOAT DEFAULT 10000.00 NOT NULL,
                platform_fee_percentage FLOAT DEFAULT 7.50 NOT NULL,
                escrow_hold_days INTEGER DEFAULT 3 NOT NULL,
                auto_approve_after_days INTEGER DEFAULT 14 NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW() NOT NULL,
                updated_by_admin_id INTEGER REFERENCES users(id)
            )
        """))
        
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_bounty_settings_id ON bounty_settings(id)"))
        
        # Create user_bounty_bans table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_bounty_bans (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) UNIQUE,
                banned_by_admin_id INTEGER NOT NULL REFERENCES users(id),
                reason TEXT NOT NULL,
                banned_at TIMESTAMP DEFAULT NOW() NOT NULL,
                expires_at TIMESTAMP,
                is_permanent BOOLEAN DEFAULT FALSE NOT NULL
            )
        """))
        
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_user_bounty_bans_id ON user_bounty_bans(id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_user_bounty_bans_user_id ON user_bounty_bans(user_id)"))
        
        # Create admin_bounty_actions table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS admin_bounty_actions (
                id SERIAL PRIMARY KEY,
                admin_id INTEGER NOT NULL REFERENCES users(id),
                bounty_id INTEGER REFERENCES bounties(id),
                action_type VARCHAR(100) NOT NULL,
                details JSON DEFAULT '{}',
                created_at TIMESTAMP DEFAULT NOW() NOT NULL
            )
        """))
        
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_admin_bounty_actions_id ON admin_bounty_actions(id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_admin_bounty_actions_admin_id ON admin_bounty_actions(admin_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_admin_bounty_actions_bounty_id ON admin_bounty_actions(bounty_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_admin_bounty_actions_created_at ON admin_bounty_actions(created_at)"))
        
        # Insert default settings
        await conn.execute(text("""
            INSERT INTO bounty_settings (
                min_bounty_amount,
                max_bounty_amount,
                platform_fee_percentage,
                escrow_hold_days,
                auto_approve_after_days
            ) VALUES (10.00, 10000.00, 7.50, 3, 14)
            ON CONFLICT DO NOTHING
        """))
        
    print("✓ Admin bounty tables created successfully")

async def main():
    """Main function"""
    print("=" * 60)
    print("Admin Bounty System Database Setup")
    print("=" * 60)
    
    # Get database URL
    database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(database_url, echo=False)
    
    try:
        await create_admin_tables(engine)
        
        print("\n✅ Admin bounty system database setup complete!")
        print("\n" + "=" * 60)
        print("Admin features added:")
        print("- Dispute management")
        print("- Settings configuration")
        print("- User ban system")
        print("- Action logging")
        print("- Admin statistics")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Restart the server")
        print("2. Visit: http://localhost:8000/docs")
        print("3. Look for 'Admin Bounties' section with 13 endpoints")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
