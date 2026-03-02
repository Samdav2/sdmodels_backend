import asyncio
from sqlalchemy import text
from app.db.session import async_session

async def add_creators_as_members():
    """Add community creators as admin members"""
    async with async_session() as session:
        # Get all communities
        result = await session.execute(text("""
            SELECT id, creator_id, name 
            FROM communities
        """))
        communities = result.fetchall()
        
        print(f"Found {len(communities)} communities")
        
        added_count = 0
        for comm_id, creator_id, name in communities:
            # Check if creator is already a member
            result = await session.execute(text("""
                SELECT id FROM community_members 
                WHERE community_id = :comm_id AND user_id = :creator_id
            """), {"comm_id": comm_id, "creator_id": creator_id})
            
            existing = result.fetchone()
            
            if not existing:
                # Add creator as admin member
                await session.execute(text("""
                    INSERT INTO community_members (community_id, user_id, role, joined_at)
                    VALUES (:comm_id, :creator_id, 'admin', NOW())
                """), {"comm_id": comm_id, "creator_id": creator_id})
                
                # Increment member count
                await session.execute(text("""
                    UPDATE communities 
                    SET member_count = member_count + 1
                    WHERE id = :comm_id
                """), {"comm_id": comm_id})
                
                print(f"✓ Added creator as admin to: {name}")
                added_count += 1
            else:
                print(f"  Creator already member of: {name}")
        
        await session.commit()
        
        print(f"\n✓ Added {added_count} creators as admin members")
        
        # Verify
        result = await session.execute(text("""
            SELECT c.name, c.member_count, COUNT(cm.id) as actual_members
            FROM communities c
            LEFT JOIN community_members cm ON c.id = cm.community_id
            GROUP BY c.id, c.name, c.member_count
        """))
        
        print("\n📊 Community member counts:")
        for name, reported_count, actual_count in result.fetchall():
            print(f"  {name}: {actual_count} members (reported: {reported_count})")

if __name__ == "__main__":
    asyncio.run(add_creators_as_members())
