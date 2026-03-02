#!/usr/bin/env python3
"""
Script to set up bounty tables in the database.
Handles the case where tables already exist.
"""
import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

async def check_table_exists(engine, table_name):
    """Check if a table exists in the database"""
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT EXISTS (SELECT FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = :table_name)"
            ),
            {"table_name": table_name}
        )
        return result.scalar()

async def drop_bounty_tables(engine):
    """Drop all bounty-related tables"""
    print("Dropping existing bounty tables...")
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS escrow_transactions CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS bounty_submissions CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS bounty_applications CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS bounties CASCADE"))
    print("✓ Existing tables dropped")

async def create_bounty_tables(engine):
    """Create bounty tables"""
    print("Creating bounty tables...")
    async with engine.begin() as conn:
        # Create bounties table
        await conn.execute(text("""
            CREATE TABLE bounties (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                budget FLOAT NOT NULL,
                deadline DATE NOT NULL,
                category VARCHAR(100) NOT NULL,
                difficulty VARCHAR(20) NOT NULL,
                status VARCHAR(50) DEFAULT 'open' NOT NULL,
                requirements JSON NOT NULL,
                poster_id INTEGER NOT NULL REFERENCES users(id),
                claimed_by_id INTEGER REFERENCES users(id),
                claimed_at TIMESTAMP,
                submitted_at TIMESTAMP,
                completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW() NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW() NOT NULL,
                CONSTRAINT check_difficulty CHECK (difficulty IN ('easy', 'medium', 'hard')),
                CONSTRAINT check_status CHECK (status IN ('open', 'claimed', 'in_progress', 'submitted', 'completed', 'cancelled'))
            )
        """))
        
        # Create indexes for bounties
        await conn.execute(text("CREATE INDEX ix_bounties_id ON bounties(id)"))
        await conn.execute(text("CREATE INDEX ix_bounties_status ON bounties(status)"))
        await conn.execute(text("CREATE INDEX ix_bounties_category ON bounties(category)"))
        await conn.execute(text("CREATE INDEX ix_bounties_poster_id ON bounties(poster_id)"))
        await conn.execute(text("CREATE INDEX ix_bounties_claimed_by_id ON bounties(claimed_by_id)"))
        
        # Create bounty_applications table
        await conn.execute(text("""
            CREATE TABLE bounty_applications (
                id SERIAL PRIMARY KEY,
                bounty_id INTEGER NOT NULL REFERENCES bounties(id) ON DELETE CASCADE,
                applicant_id INTEGER NOT NULL REFERENCES users(id),
                proposal TEXT NOT NULL,
                estimated_delivery DATE NOT NULL,
                portfolio_links JSON,
                status VARCHAR(20) DEFAULT 'pending' NOT NULL,
                created_at TIMESTAMP DEFAULT NOW() NOT NULL,
                CONSTRAINT check_application_status CHECK (status IN ('pending', 'approved', 'rejected')),
                CONSTRAINT uq_bounty_applicant UNIQUE (bounty_id, applicant_id)
            )
        """))
        
        # Create indexes for applications
        await conn.execute(text("CREATE INDEX ix_bounty_applications_id ON bounty_applications(id)"))
        await conn.execute(text("CREATE INDEX ix_bounty_applications_bounty_id ON bounty_applications(bounty_id)"))
        await conn.execute(text("CREATE INDEX ix_bounty_applications_applicant_id ON bounty_applications(applicant_id)"))
        
        # Create bounty_submissions table
        await conn.execute(text("""
            CREATE TABLE bounty_submissions (
                id SERIAL PRIMARY KEY,
                bounty_id INTEGER NOT NULL REFERENCES bounties(id) ON DELETE CASCADE UNIQUE,
                artist_id INTEGER NOT NULL REFERENCES users(id),
                model_url VARCHAR(500) NOT NULL,
                preview_images JSON,
                notes TEXT,
                status VARCHAR(50) DEFAULT 'pending' NOT NULL,
                feedback TEXT,
                submitted_at TIMESTAMP DEFAULT NOW() NOT NULL,
                reviewed_at TIMESTAMP,
                CONSTRAINT check_submission_status CHECK (status IN ('pending', 'approved', 'rejected', 'revision_requested'))
            )
        """))
        
        # Create indexes for submissions
        await conn.execute(text("CREATE INDEX ix_bounty_submissions_id ON bounty_submissions(id)"))
        await conn.execute(text("CREATE UNIQUE INDEX ix_bounty_submissions_bounty_id ON bounty_submissions(bounty_id)"))
        
        # Create escrow_transactions table
        await conn.execute(text("""
            CREATE TABLE escrow_transactions (
                id SERIAL PRIMARY KEY,
                bounty_id INTEGER NOT NULL REFERENCES bounties(id),
                buyer_id INTEGER NOT NULL REFERENCES users(id),
                artist_id INTEGER REFERENCES users(id),
                amount FLOAT NOT NULL,
                platform_fee FLOAT NOT NULL,
                status VARCHAR(50) DEFAULT 'held' NOT NULL,
                held_at TIMESTAMP DEFAULT NOW() NOT NULL,
                released_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW() NOT NULL,
                CONSTRAINT check_escrow_status CHECK (status IN ('held', 'released', 'refunded'))
            )
        """))
        
        # Create indexes for escrow
        await conn.execute(text("CREATE INDEX ix_escrow_transactions_id ON escrow_transactions(id)"))
        await conn.execute(text("CREATE INDEX ix_escrow_transactions_bounty_id ON escrow_transactions(bounty_id)"))
        
    print("✓ Bounty tables created successfully")

async def main():
    """Main function"""
    print("=" * 60)
    print("Bounty System Database Setup")
    print("=" * 60)
    
    # Get database URL
    database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(database_url, echo=False)
    
    try:
        # Check if tables exist
        bounties_exist = await check_table_exists(engine, "bounties")
        
        if bounties_exist:
            print("\n⚠️  Bounty tables already exist!")
            print("\nOptions:")
            print("1. Drop and recreate tables (WARNING: All data will be lost)")
            print("2. Skip setup (tables already exist)")
            print("3. Exit")
            
            choice = input("\nEnter your choice (1/2/3): ").strip()
            
            if choice == "1":
                confirm = input("\n⚠️  Are you sure? This will DELETE ALL bounty data! (yes/no): ").strip().lower()
                if confirm == "yes":
                    await drop_bounty_tables(engine)
                    await create_bounty_tables(engine)
                    print("\n✅ Bounty tables recreated successfully!")
                else:
                    print("\n❌ Operation cancelled")
                    return
            elif choice == "2":
                print("\n✓ Skipping setup - tables already exist")
                return
            else:
                print("\n❌ Exiting")
                return
        else:
            # Tables don't exist, create them
            await create_bounty_tables(engine)
            print("\n✅ Bounty system database setup complete!")
        
        print("\n" + "=" * 60)
        print("Next steps:")
        print("1. Start the server: uvicorn app.main:app --reload")
        print("2. Visit: http://localhost:8000/docs")
        print("3. Look for 'Bounties' section with 18 endpoints")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
