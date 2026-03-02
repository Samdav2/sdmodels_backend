#!/usr/bin/env python3
"""
Migrate bounty chat system from per-bounty to per-user-pair
This allows users to have one conversation across all their bounties
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.session import engine


async def migrate_chat_system():
    """Migrate chat system to user-pair based"""
    print("=" * 60)
    print("MIGRATING BOUNTY CHAT SYSTEM")
    print("=" * 60)
    
    async with engine.begin() as conn:
        print("\n1. Adding bounty_id to messages table...")
        await conn.execute(text("""
            ALTER TABLE bounty_chat_messages 
            ADD COLUMN IF NOT EXISTS bounty_id UUID REFERENCES bounties(id) ON DELETE SET NULL;
        """))
        print("✓ Added bounty_id column to messages")
        
        print("\n2. Migrating existing message data...")
        # Copy bounty_id from chat to messages
        await conn.execute(text("""
            UPDATE bounty_chat_messages 
            SET bounty_id = bounty_chats.bounty_id
            FROM bounty_chats
            WHERE bounty_chat_messages.chat_id = bounty_chats.id
            AND bounty_chat_messages.bounty_id IS NULL;
        """))
        print("✓ Migrated existing message bounty references")
        
        print("\n3. Removing unique constraint on bounty_id in chats...")
        # Drop the unique constraint on bounty_id
        await conn.execute(text("""
            ALTER TABLE bounty_chats 
            DROP CONSTRAINT IF EXISTS bounty_chats_bounty_id_key;
        """))
        print("✓ Removed unique constraint")
        
        print("\n4. Making bounty_id nullable in chats...")
        await conn.execute(text("""
            ALTER TABLE bounty_chats 
            ALTER COLUMN bounty_id DROP NOT NULL;
        """))
        print("✓ Made bounty_id nullable")
        
        print("\n5. Consolidating chats for same user pairs...")
        # Find and merge duplicate chats for same user pairs
        result = await conn.execute(text("""
            WITH user_pairs AS (
                SELECT 
                    LEAST(client_id, artist_id) as user1,
                    GREATEST(client_id, artist_id) as user2,
                    (array_agg(id ORDER BY created_at))[1] as keep_chat_id,
                    array_agg(id ORDER BY created_at) as all_chat_ids
                FROM bounty_chats
                WHERE artist_id IS NOT NULL
                GROUP BY LEAST(client_id, artist_id), GREATEST(client_id, artist_id)
                HAVING COUNT(*) > 1
            )
            SELECT user1, user2, keep_chat_id, all_chat_ids
            FROM user_pairs;
        """))
        
        duplicates = result.fetchall()
        if duplicates:
            print(f"   Found {len(duplicates)} user pairs with multiple chats")
            for dup in duplicates:
                user1, user2, keep_id, all_ids = dup
                merge_ids = [id for id in all_ids if id != keep_id]
                
                # Move messages from duplicate chats to the kept chat
                for merge_id in merge_ids:
                    await conn.execute(text("""
                        UPDATE bounty_chat_messages 
                        SET chat_id = :keep_id 
                        WHERE chat_id = :merge_id;
                    """), {"keep_id": keep_id, "merge_id": merge_id})
                    
                    # Delete the duplicate chat
                    await conn.execute(text("""
                        DELETE FROM bounty_chats WHERE id = :merge_id;
                    """), {"merge_id": merge_id})
                
                print(f"   ✓ Merged {len(merge_ids)} duplicate chats for user pair")
        else:
            print("   No duplicate chats found")
        
        print("\n6. Creating unique constraint on user pairs...")
        # Create unique constraint on client_id + artist_id
        await conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_bounty_chats_user_pair 
            ON bounty_chats(LEAST(client_id, artist_id), GREATEST(client_id, artist_id))
            WHERE artist_id IS NOT NULL;
        """))
        print("✓ Created unique constraint on user pairs")
        
        print("\n7. Creating index on message bounty_id...")
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_bounty_chat_messages_bounty_id 
            ON bounty_chat_messages(bounty_id);
        """))
        print("✓ Created index on message bounty_id")
        
        print("\n8. Updating chat last_message_at timestamps...")
        await conn.execute(text("""
            UPDATE bounty_chats
            SET last_message_at = (
                SELECT MAX(created_at)
                FROM bounty_chat_messages
                WHERE bounty_chat_messages.chat_id = bounty_chats.id
            )
            WHERE EXISTS (
                SELECT 1 FROM bounty_chat_messages 
                WHERE bounty_chat_messages.chat_id = bounty_chats.id
            );
        """))
        print("✓ Updated last message timestamps")
    
    print("\n" + "=" * 60)
    print("✓ MIGRATION COMPLETE")
    print("=" * 60)
    print("\nChanges:")
    print("- Chats are now per user-pair (not per bounty)")
    print("- Messages have bounty_id to show context")
    print("- Duplicate chats have been merged")
    print("- All existing messages preserved with bounty context")


if __name__ == "__main__":
    asyncio.run(migrate_chat_system())
