import asyncio
from sqlalchemy import text
from app.db.session import async_session

async def activate_communities():
    """Update all pending communities to active status"""
    async with async_session() as session:
        # Update all pending communities to active
        result = await session.execute(text("""
            UPDATE communities 
            SET status = 'active' 
            WHERE status = 'pending'
            RETURNING id, name
        """))
        
        updated = result.fetchall()
        await session.commit()
        
        print(f"✓ Updated {len(updated)} communities to active status")
        
        if updated:
            print("\nActivated communities:")
            for comm_id, name in updated:
                print(f"  - {name} ({comm_id})")
        
        # Verify
        result = await session.execute(text("""
            SELECT status, COUNT(*) 
            FROM communities 
            GROUP BY status
        """))
        status_counts = result.fetchall()
        
        print("\n📈 Communities by status:")
        for status, count in status_counts:
            print(f"  {status}: {count}")

if __name__ == "__main__":
    asyncio.run(activate_communities())
