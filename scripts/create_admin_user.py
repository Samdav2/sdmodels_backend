#!/usr/bin/env python3
"""
Script to create or promote a user to admin.
"""
import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.core.security import get_password_hash

async def create_admin_user(engine, email: str, password: str, username: str):
    """Create a new admin user"""
    async with engine.begin() as conn:
        # Check if user exists
        result = await conn.execute(
            text("SELECT id, user_type FROM users WHERE email = :email"),
            {"email": email}
        )
        existing_user = result.fetchone()
        
        if existing_user:
            user_id, current_type = existing_user
            if current_type == "admin":
                print(f"✓ User {email} is already an admin")
                return
            
            # Promote to admin
            await conn.execute(
                text("UPDATE users SET user_type = 'admin' WHERE id = :user_id"),
                {"user_id": user_id}
            )
            print(f"✓ User {email} promoted to admin")
        else:
            # Create new admin user
            password_hash = get_password_hash(password)
            await conn.execute(
                text("""
                    INSERT INTO users (
                        email, username, password_hash, user_type, 
                        is_active, is_verified, created_at, updated_at
                    ) VALUES (
                        :email, :username, :password_hash, 'admin',
                        true, true, NOW(), NOW()
                    )
                """),
                {
                    "email": email,
                    "username": username,
                    "password_hash": password_hash
                }
            )
            print(f"✓ Admin user {email} created successfully")

async def promote_user_to_admin(engine, email: str):
    """Promote an existing user to admin"""
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT id, user_type FROM users WHERE email = :email"),
            {"email": email}
        )
        user = result.fetchone()
        
        if not user:
            print(f"✗ User {email} not found")
            return False
        
        user_id, current_type = user
        if current_type == "admin":
            print(f"✓ User {email} is already an admin")
            return True
        
        await conn.execute(
            text("UPDATE users SET user_type = 'admin' WHERE id = :user_id"),
            {"user_id": user_id}
        )
        print(f"✓ User {email} promoted to admin")
        return True

async def list_admins(engine):
    """List all admin users"""
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT id, email, username, created_at FROM users WHERE user_type = 'admin' ORDER BY id")
        )
        admins = result.fetchall()
        
        if not admins:
            print("No admin users found")
            return
        
        print("\nAdmin Users:")
        print("-" * 80)
        print(f"{'ID':<6} {'Email':<30} {'Username':<20} {'Created':<20}")
        print("-" * 80)
        for admin in admins:
            admin_id, email, username, created_at = admin
            created_str = created_at.strftime("%Y-%m-%d %H:%M") if created_at else "N/A"
            print(f"{admin_id:<6} {email:<30} {username:<20} {created_str:<20}")
        print("-" * 80)

async def main():
    """Main function"""
    print("=" * 60)
    print("Admin User Management")
    print("=" * 60)
    
    database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(database_url, echo=False)
    
    try:
        print("\nOptions:")
        print("1. Create new admin user")
        print("2. Promote existing user to admin")
        print("3. List all admin users")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1/2/3/4): ").strip()
        
        if choice == "1":
            print("\n--- Create New Admin User ---")
            email = input("Email: ").strip()
            username = input("Username: ").strip()
            password = input("Password: ").strip()
            
            if not email or not username or not password:
                print("✗ All fields are required")
                return
            
            await create_admin_user(engine, email, password, username)
            
        elif choice == "2":
            print("\n--- Promote User to Admin ---")
            email = input("User email: ").strip()
            
            if not email:
                print("✗ Email is required")
                return
            
            await promote_user_to_admin(engine, email)
            
        elif choice == "3":
            await list_admins(engine)
            
        elif choice == "4":
            print("Exiting...")
            return
        else:
            print("✗ Invalid choice")
            return
        
        print("\n" + "=" * 60)
        print("✅ Operation completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
