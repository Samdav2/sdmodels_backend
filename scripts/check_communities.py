import asyncio
from sqlalchemy import text
from app.db.session import async_session

async def check_communities():
    """Check communities in database"""
    async with async_session() as session:
        # Check if communities table exists
        result = await session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'communities'
        """))
        table_exists = result.fetchone()
        
        if not table_exists:
            print("❌ Communities table does not exist!")
            return
        
        print("✓ Communities table exists")
        
        # Get all communities
        result = await session.execute(text("""
            SELECT id, name, description, category, status, creator_id, 
                   member_count, post_count, created_at
            FROM communities
        """))
        communities = result.fetchall()
        
        print(f"\n📊 Total communities in database: {len(communities)}")
        
        if communities:
            print("\nCommunities:")
            for comm in communities:
                print(f"\n  ID: {comm[0]}")
                print(f"  Name: {comm[1]}")
                print(f"  Description: {comm[2]}")
                print(f"  Category: {comm[3]}")
                print(f"  Status: {comm[4]}")
                print(f"  Creator ID: {comm[5]}")
                print(f"  Members: {comm[6]}")
                print(f"  Posts: {comm[7]}")
                print(f"  Created: {comm[8]}")
        else:
            print("\n⚠️  No communities found in database")
        
        # Check status distribution
        result = await session.execute(text("""
            SELECT status, COUNT(*) 
            FROM communities 
            GROUP BY status
        """))
        status_counts = result.fetchall()
        
        if status_counts:
            print("\n📈 Communities by status:")
            for status, count in status_counts:
                print(f"  {status}: {count}")

if __name__ == "__main__":
    asyncio.run(check_communities())
