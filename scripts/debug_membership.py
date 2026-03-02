import asyncio
from sqlalchemy import text
from uuid import UUID
from app.db.session import async_session

COMMUNITY_ID = "29d43076-4710-4025-a8bf-934eec0c96f7"
USER_ID = "82c10cb6-f888-4387-8c9c-3eb27c859fb8"

async def debug_membership():
    """Debug membership detection"""
    async with async_session() as session:
        print("=" * 60)
        print("DEBUGGING MEMBERSHIP DETECTION")
        print("=" * 60)
        
        # Check if community exists
        print(f"\n1. Checking community: {COMMUNITY_ID}")
        result = await session.execute(text("""
            SELECT id, name, creator_id 
            FROM communities 
            WHERE id = :comm_id
        """), {"comm_id": UUID(COMMUNITY_ID)})
        
        community = result.fetchone()
        if community:
            print(f"✓ Community found: {community[1]}")
            print(f"  Creator ID: {community[2]}")
        else:
            print("✗ Community not found!")
            return
        
        # Check if user exists
        print(f"\n2. Checking user: {USER_ID}")
        result = await session.execute(text("""
            SELECT id, username, email 
            FROM users 
            WHERE id = :user_id
        """), {"user_id": UUID(USER_ID)})
        
        user = result.fetchone()
        if user:
            print(f"✓ User found: {user[1]} ({user[2]})")
        else:
            print("✗ User not found!")
            return
        
        # Check membership
        print(f"\n3. Checking membership...")
        result = await session.execute(text("""
            SELECT id, user_id, community_id, role, joined_at
            FROM community_members 
            WHERE user_id = :user_id AND community_id = :comm_id
        """), {"user_id": UUID(USER_ID), "comm_id": UUID(COMMUNITY_ID)})
        
        membership = result.fetchone()
        if membership:
            print(f"✓ Membership found!")
            print(f"  Membership ID: {membership[0]}")
            print(f"  User ID: {membership[1]}")
            print(f"  Community ID: {membership[2]}")
            print(f"  Role: {membership[3]}")
            print(f"  Joined at: {membership[4]}")
        else:
            print("✗ Membership NOT found!")
            print("\nThis is the problem! User should be a member.")
            return
        
        # Test the repository method
        print(f"\n4. Testing repository get_membership method...")
        from app.repositories.community_repository import CommunityRepository
        
        repo = CommunityRepository(session)
        membership_obj = await repo.get_membership(UUID(USER_ID), UUID(COMMUNITY_ID))
        
        if membership_obj:
            print(f"✓ Repository method works!")
            print(f"  Role: {membership_obj.role}")
        else:
            print("✗ Repository method returned None!")
            print("  This is a bug in the repository method")
        
        print("\n" + "=" * 60)
        print("CONCLUSION:")
        print("=" * 60)
        
        if membership and membership_obj:
            print("\n✓ Everything is working correctly in the database!")
            print("\nThe issue must be:")
            print("  1. Token is not being sent from frontend")
            print("  2. Token is invalid/expired")
            print("  3. Token contains wrong user_id")
            print("  4. get_optional_user is returning None")
            
            print("\nTo debug further:")
            print("  1. Check browser DevTools Network tab")
            print("  2. Verify Authorization header is present")
            print("  3. Decode the JWT token to check user_id")
            print("  4. Add logging to get_optional_user dependency")
        else:
            print("\n✗ Database issue detected!")
            print("  User is not properly registered as a member")

if __name__ == "__main__":
    asyncio.run(debug_membership())
