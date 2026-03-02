"""
Enhance bounty submissions table to support file uploads and external links
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.session import engine


async def enhance_submissions_table():
    """Add new columns to bounty_submissions table"""
    
    async with engine.begin() as conn:
        print("Enhancing bounty_submissions table...")
        
        # Add columns one by one
        await conn.execute(text("ALTER TABLE bounty_submissions ADD COLUMN IF NOT EXISTS submission_type VARCHAR(10) DEFAULT 'upload'"))
        await conn.execute(text("ALTER TABLE bounty_submissions ADD COLUMN IF NOT EXISTS model_file_name VARCHAR(255)"))
        await conn.execute(text("ALTER TABLE bounty_submissions ADD COLUMN IF NOT EXISTS model_file_size BIGINT"))
        await conn.execute(text("ALTER TABLE bounty_submissions ADD COLUMN IF NOT EXISTS model_format VARCHAR(10)"))
        await conn.execute(text("ALTER TABLE bounty_submissions ADD COLUMN IF NOT EXISTS external_model_url VARCHAR(500)"))
        
        print("✓ Added new columns")
        
        # Rename model_url to model_file_url
        await conn.execute(text("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'bounty_submissions' 
                    AND column_name = 'model_url'
                ) AND NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'bounty_submissions' 
                    AND column_name = 'model_file_url'
                ) THEN
                    ALTER TABLE bounty_submissions 
                    RENAME COLUMN model_url TO model_file_url;
                END IF;
            END $$;
        """))
        
        print("✓ Renamed model_url to model_file_url")
        
        # Drop old constraint if exists
        await conn.execute(text("ALTER TABLE bounty_submissions DROP CONSTRAINT IF EXISTS check_submission_status"))
        
        # Add new constraints
        await conn.execute(text("ALTER TABLE bounty_submissions ADD CONSTRAINT check_submission_status CHECK (status IN ('pending', 'approved', 'rejected', 'revision_requested'))"))
        await conn.execute(text("ALTER TABLE bounty_submissions ADD CONSTRAINT check_submission_type CHECK (submission_type IN ('upload', 'link'))"))
        
        # Drop old valid submission constraint if exists
        await conn.execute(text("ALTER TABLE bounty_submissions DROP CONSTRAINT IF EXISTS check_valid_submission"))
        
        # Add valid submission constraint
        await conn.execute(text("""
            ALTER TABLE bounty_submissions 
            ADD CONSTRAINT check_valid_submission 
            CHECK (
                (submission_type = 'upload' AND model_file_url IS NOT NULL) OR 
                (submission_type = 'link' AND external_model_url IS NOT NULL)
            )
        """))
        
        print("✓ Added constraints")
        
        # Migrate existing data
        await conn.execute(text("""
            UPDATE bounty_submissions 
            SET submission_type = 'link', 
                external_model_url = model_file_url
            WHERE submission_type IS NULL OR submission_type = 'upload'
        """))
        
        print("✓ Migrated existing data")
        
        print("\n✅ Bounty submissions table enhanced successfully!")
        print("\nNew features:")
        print("  - Support for file uploads (GLB, FBX, OBJ, BLEND, etc.)")
        print("  - Support for external links (Sketchfab, ArtStation, etc.)")
        print("  - File metadata tracking (name, size, format)")
        print("  - Preview image support")


async def verify_schema():
    """Verify the schema changes"""
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'bounty_submissions'
            ORDER BY ordinal_position;
        """))
        
        print("\n📋 Current bounty_submissions schema:")
        print("-" * 60)
        for row in result:
            col_name, data_type, max_length = row
            length_str = f"({max_length})" if max_length else ""
            print(f"  {col_name:<30} {data_type}{length_str}")


async def main():
    """Main execution"""
    try:
        await enhance_submissions_table()
        await verify_schema()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
