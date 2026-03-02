import asyncio
from sqlalchemy import text
from app.db.session import async_session

async def create_comment_likes_table():
    """Create comment_likes table"""
    async with async_session() as session:
        print("Creating comment_likes table...")
        
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS comment_likes (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                comment_id UUID NOT NULL REFERENCES post_comments(id) ON DELETE CASCADE,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE(comment_id, user_id)
            )
        """))
        
        # Create indexes
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_comment_likes_comment_id 
            ON comment_likes(comment_id)
        """))
        
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_comment_likes_user_id 
            ON comment_likes(user_id)
        """))
        
        await session.commit()
        
        print("✓ comment_likes table created successfully")
        print("✓ Indexes created")
        
        # Verify
        result = await session.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'comment_likes'
            ORDER BY ordinal_position
        """))
        
        columns = result.fetchall()
        print("\nTable structure:")
        for col_name, col_type in columns:
            print(f"  {col_name}: {col_type}")

if __name__ == "__main__":
    asyncio.run(create_comment_likes_table())
