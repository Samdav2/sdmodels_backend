"""
Check the most recently created bounty
"""
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.session import engine


async def check_bounty():
    async with engine.begin() as conn:
        # Get the most recent bounty
        result = await conn.execute(text("""
            SELECT id, title, budget, poster_id, created_at
            FROM bounties
            ORDER BY created_at DESC
            LIMIT 1
        """))
        
        bounty = result.fetchone()
        
        if bounty:
            print("✅ Most recent bounty:")
            print(f"   ID: {bounty[0]} (type: {type(bounty[0])})")
            print(f"   Title: {bounty[1]}")
            print(f"   Budget: ${bounty[2]}")
            print(f"   Poster ID: {bounty[3]}")
            print(f"   Created: {bounty[4]}")
        else:
            print("❌ No bounties found")


if __name__ == "__main__":
    asyncio.run(check_bounty())
