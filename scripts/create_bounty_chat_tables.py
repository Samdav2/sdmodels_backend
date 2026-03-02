"""
Create bounty chat system tables
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.session import engine


async def create_chat_tables():
    """Create bounty chat tables"""
    print("Creating bounty chat tables...")
    
    async with engine.begin() as conn:
        # Create bounty_chats table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS bounty_chats (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                bounty_id UUID UNIQUE NOT NULL REFERENCES bounties(id) ON DELETE CASCADE,
                client_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                artist_id UUID REFERENCES users(id) ON DELETE SET NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_message_at TIMESTAMP
            );
        """))
        print("✓ Created bounty_chats table")
        
        # Create bounty_chat_messages table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS bounty_chat_messages (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                chat_id UUID NOT NULL REFERENCES bounty_chats(id) ON DELETE CASCADE,
                sender_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                message_type VARCHAR(20) NOT NULL,
                content TEXT,
                file_url VARCHAR(500),
                file_name VARCHAR(255),
                file_size INTEGER,
                file_type VARCHAR(50),
                voice_duration INTEGER,
                thumbnail_url VARCHAR(500),
                reply_to_id UUID REFERENCES bounty_chat_messages(id) ON DELETE SET NULL,
                is_edited BOOLEAN DEFAULT FALSE,
                is_deleted BOOLEAN DEFAULT FALSE,
                is_read BOOLEAN DEFAULT FALSE,
                read_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT valid_message_type CHECK (
                    message_type IN ('text', 'image', 'voice', 'link', 'file')
                )
            );
        """))
        print("✓ Created bounty_chat_messages table")
        
        # Create bounty_chat_attachments table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS bounty_chat_attachments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                message_id UUID NOT NULL REFERENCES bounty_chat_messages(id) ON DELETE CASCADE,
                file_url VARCHAR(500) NOT NULL,
                file_name VARCHAR(255) NOT NULL,
                file_size INTEGER NOT NULL,
                file_type VARCHAR(50) NOT NULL,
                thumbnail_url VARCHAR(500),
                width INTEGER,
                height INTEGER,
                "order" INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        print("✓ Created bounty_chat_attachments table")
        
        # Create indexes
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_bounty_chats_bounty_id ON bounty_chats(bounty_id);
        """))
        
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_bounty_chats_client_id ON bounty_chats(client_id);
        """))
        
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_bounty_chats_artist_id ON bounty_chats(artist_id);
        """))
        
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_bounty_chat_messages_chat_id ON bounty_chat_messages(chat_id);
        """))
        
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_bounty_chat_messages_sender_id ON bounty_chat_messages(sender_id);
        """))
        
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_bounty_chat_messages_created_at ON bounty_chat_messages(created_at DESC);
        """))
        
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_bounty_chat_attachments_message_id ON bounty_chat_attachments(message_id);
        """))
        
        print("✓ Created indexes")


async def verify_chat_system():
    """Verify chat system is working"""
    print("\nVerifying chat system...")
    
    async with engine.begin() as conn:
        # Check tables exist
        result = await conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('bounty_chats', 'bounty_chat_messages', 'bounty_chat_attachments')
            ORDER BY table_name
        """))
        tables = [row[0] for row in result.fetchall()]
        
        if len(tables) == 3:
            print("✓ All chat tables created successfully")
            for table in tables:
                print(f"  - {table}")
        else:
            print(f"⚠ Warning: Expected 3 tables, found {len(tables)}")


async def main():
    """Main function"""
    print("=" * 60)
    print("BOUNTY CHAT SYSTEM SETUP")
    print("=" * 60)
    
    try:
        # Create tables
        await create_chat_tables()
        
        # Verify
        await verify_chat_system()
        
        print("\n" + "=" * 60)
        print("✓ BOUNTY CHAT SYSTEM SETUP COMPLETE")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Restart your FastAPI server")
        print("2. Test chat endpoints:")
        print("   - GET /api/v1/bounty-chat/my-chats")
        print("   - GET /api/v1/bounty-chat/bounty/{bounty_id}")
        print("   - POST /api/v1/bounty-chat/bounty/{bounty_id}/messages/text")
        print("   - POST /api/v1/bounty-chat/bounty/{bounty_id}/messages/image")
        print("   - POST /api/v1/bounty-chat/bounty/{bounty_id}/messages/voice")
        print("3. Clients and artists can now chat about bounties!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
