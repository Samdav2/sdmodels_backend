"""
Script to enhance bounty system with milestones, deadline extensions, and revision tracking.
Adds new tables and columns to support full freelance platform features.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.session import engine


async def enhance_bounty_system():
    """Add milestone system, deadline extensions, and revision tracking"""
    
    async with engine.begin() as conn:
        print("🚀 Enhancing bounty system...")
        
        # 1. Add new columns to bounties table
        print("\n1️⃣ Adding new columns to bounties table...")
        try:
            await conn.execute(text("""
                ALTER TABLE bounties 
                ADD COLUMN IF NOT EXISTS has_milestones BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS max_revisions INTEGER DEFAULT 3,
                ADD COLUMN IF NOT EXISTS revision_count INTEGER DEFAULT 0;
            """))
            print("   ✅ Added has_milestones, max_revisions, revision_count columns")
        except Exception as e:
            print(f"   ⚠️  Columns may already exist: {e}")
        
        # Fix claimed_by_id to UUID if needed
        try:
            await conn.execute(text("""
                ALTER TABLE bounties 
                ALTER COLUMN claimed_by_id TYPE UUID USING claimed_by_id::uuid;
            """))
            print("   ✅ Fixed claimed_by_id to UUID type")
        except Exception as e:
            print(f"   ℹ️  claimed_by_id already UUID: {e}")
        
        # 2. Create bounty_milestones table
        print("\n2️⃣ Creating bounty_milestones table...")
        try:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS bounty_milestones (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    bounty_id UUID NOT NULL REFERENCES bounties(id) ON DELETE CASCADE,
                    title VARCHAR(255) NOT NULL,
                    description TEXT NOT NULL,
                    amount FLOAT NOT NULL,
                    deadline DATE NOT NULL,
                    "order" INTEGER DEFAULT 1,
                    status VARCHAR(50) DEFAULT 'pending',
                    started_at TIMESTAMP,
                    submitted_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    CONSTRAINT check_milestone_status CHECK (status IN ('pending', 'in_progress', 'submitted', 'completed', 'cancelled'))
                );
            """))
            print("   ✅ Created bounty_milestones table")
        except Exception as e:
            print(f"   ⚠️  Table may already exist: {e}")
        
        # 3. Create deadline_extension_requests table
        print("\n3️⃣ Creating deadline_extension_requests table...")
        try:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS deadline_extension_requests (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    bounty_id UUID NOT NULL REFERENCES bounties(id) ON DELETE CASCADE,
                    milestone_id UUID REFERENCES bounty_milestones(id) ON DELETE CASCADE,
                    artist_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    current_deadline DATE NOT NULL,
                    requested_deadline DATE NOT NULL,
                    reason TEXT NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    response_message TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    responded_at TIMESTAMP,
                    CONSTRAINT check_extension_status CHECK (status IN ('pending', 'approved', 'rejected'))
                );
            """))
            print("   ✅ Created deadline_extension_requests table")
        except Exception as e:
            print(f"   ⚠️  Table may already exist: {e}")
        
        # 4. Update escrow_transactions table
        print("\n4️⃣ Updating escrow_transactions table...")
        try:
            await conn.execute(text("""
                ALTER TABLE escrow_transactions 
                ADD COLUMN IF NOT EXISTS milestone_id UUID REFERENCES bounty_milestones(id) ON DELETE CASCADE;
            """))
            print("   ✅ Added milestone_id column to escrow_transactions")
        except Exception as e:
            print(f"   ⚠️  Column may already exist: {e}")
        
        # Fix artist_id to UUID if needed
        try:
            await conn.execute(text("""
                ALTER TABLE escrow_transactions 
                ALTER COLUMN artist_id TYPE UUID USING artist_id::uuid;
            """))
            print("   ✅ Fixed artist_id to UUID type")
        except Exception as e:
            print(f"   ℹ️  artist_id already UUID: {e}")
        
        # 5. Update bounty_submissions table
        print("\n5️⃣ Updating bounty_submissions table...")
        
        # Remove unique constraint on bounty_id
        try:
            await conn.execute(text("""
                ALTER TABLE bounty_submissions 
                DROP CONSTRAINT IF EXISTS bounty_submissions_bounty_id_key;
            """))
            print("   ✅ Removed unique constraint on bounty_id")
        except Exception as e:
            print(f"   ℹ️  Constraint may not exist: {e}")
        
        # Add new columns
        try:
            await conn.execute(text("""
                ALTER TABLE bounty_submissions 
                ADD COLUMN IF NOT EXISTS milestone_id UUID REFERENCES bounty_milestones(id) ON DELETE CASCADE,
                ADD COLUMN IF NOT EXISTS revision_number INTEGER DEFAULT 1;
            """))
            print("   ✅ Added milestone_id and revision_number columns")
        except Exception as e:
            print(f"   ⚠️  Columns may already exist: {e}")
        
        # 6. Create indexes for performance
        print("\n6️⃣ Creating indexes...")
        indexes = [
            ("idx_milestones_bounty", "bounty_milestones", "bounty_id"),
            ("idx_milestones_status", "bounty_milestones", "status"),
            ("idx_extensions_bounty", "deadline_extension_requests", "bounty_id"),
            ("idx_extensions_status", "deadline_extension_requests", "status"),
            ("idx_escrow_milestone", "escrow_transactions", "milestone_id"),
            ("idx_submissions_milestone", "bounty_submissions", "milestone_id"),
        ]
        
        for idx_name, table_name, column_name in indexes:
            try:
                await conn.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name}({column_name});
                """))
                print(f"   ✅ Created index {idx_name}")
            except Exception as e:
                print(f"   ⚠️  Index {idx_name} may already exist: {e}")
        
        print("\n✨ Bounty system enhancement complete!")
        print("\n📋 Summary:")
        print("   • Added milestone system with multiple deliverables")
        print("   • Added deadline extension request workflow")
        print("   • Added revision tracking with configurable limits")
        print("   • Enhanced escrow with milestone-based payments")
        print("   • Created performance indexes")
        print("\n🎉 Your bounty system is now a full-fledged freelance platform!")


if __name__ == "__main__":
    asyncio.run(enhance_bounty_system())
