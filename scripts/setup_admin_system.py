#!/usr/bin/env python3
"""
Script to set up the admin system and create admin users.
Completely separate from regular user system.
"""
import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.core.security import get_password_hash

async def create_admin_table(engine):
    """Create admin_users table"""
    print("Creating admin_users table...")
    
    async with engine.begin() as conn:
        # Check if table exists
        result = await conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name = 'admin_users'
            )
        """))
        table_exists = result.scalar()
        
        if table_exists:
            print("✓ Admin users table already exists")
            return
        
        # Create table
        await conn.execute(text("""
            CREATE TABLE admin_users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                username VARCHAR(50) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                role VARCHAR(20) DEFAULT 'admin' NOT NULL,
                is_active BOOLEAN DEFAULT TRUE NOT NULL,
                avatar_url VARCHAR(500),
                created_at TIMESTAMP DEFAULT NOW() NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW() NOT NULL,
                last_login TIMESTAMP,
                can_manage_users BOOLEAN DEFAULT TRUE NOT NULL,
                can_manage_bounties BOOLEAN DEFAULT TRUE NOT NULL,
                can_manage_content BOOLEAN DEFAULT TRUE NOT NULL,
                can_manage_settings BOOLEAN DEFAULT TRUE NOT NULL,
                can_view_analytics BOOLEAN DEFAULT TRUE NOT NULL,
                CONSTRAINT admin_users_email_key UNIQUE (email),
                CONSTRAINT admin_users_username_key UNIQUE (username)
            )
        """))
        
        # Create indexes
        await conn.execute(text("CREATE INDEX ix_admin_users_id ON admin_users(id)"))
        await conn.execute(text("CREATE INDEX ix_admin_users_email ON admin_users(email)"))
        await conn.execute(text("CREATE INDEX ix_admin_users_username ON admin_users(username)"))
        await conn.execute(text("CREATE INDEX ix_admin_users_is_active ON admin_users(is_active)"))
        
    print("✓ Admin users table created successfully")

async def create_admin_user(engine, email: str, username: str, password: str, role: str = "admin"):
    """Create a new admin user"""
    async with engine.begin() as conn:
        # Check if admin exists
        result = await conn.execute(
            text("SELECT id FROM admin_users WHERE email = :email"),
            {"email": email}
        )
        existing = result.fetchone()
        
        if existing:
            print(f"✗ Admin with email {email} already exists")
            return False
        
        # Create admin
        password_hash = get_password_hash(password)
        await conn.execute(
            text("""
                INSERT INTO admin_users (
                    email, username, password_hash, role, full_name
                ) VALUES (
                    :email, :username, :password_hash, :role, :full_name
                )
            """),
            {
                "email": email,
                "username": username,
                "password_hash": password_hash,
                "role": role,
                "full_name": username.title()
            }
        )
        print(f"✓ Admin user {email} created successfully")
        return True

async def list_admins(engine):
    """List all admin users"""
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT id, email, username, role, is_active, created_at FROM admin_users ORDER BY id")
        )
        admins = result.fetchall()
        
        if not admins:
            print("\nNo admin users found")
            return
        
        print("\nAdmin Users:")
        print("-" * 100)
        print(f"{'ID':<6} {'Email':<30} {'Username':<20} {'Role':<15} {'Active':<8} {'Created':<20}")
        print("-" * 100)
        for admin in admins:
            admin_id, email, username, role, is_active, created_at = admin
            active_str = "Yes" if is_active else "No"
            created_str = created_at.strftime("%Y-%m-%d %H:%M") if created_at else "N/A"
            print(f"{admin_id:<6} {email:<30} {username:<20} {role:<15} {active_str:<8} {created_str:<20}")
        print("-" * 100)

async def main():
    """Main function"""
    print("=" * 60)
    print("Admin System Setup")
    print("=" * 60)
    
    database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(database_url, echo=False)
    
    try:
        # Create table first
        await create_admin_table(engine)
        
        print("\nOptions:")
        print("1. Create new admin user")
        print("2. Create superadmin user")
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
            
            await create_admin_user(engine, email, username, password, "admin")
            
        elif choice == "2":
            print("\n--- Create Superadmin User ---")
            email = input("Email: ").strip()
            username = input("Username: ").strip()
            password = input("Password: ").strip()
            
            if not email or not username or not password:
                print("✗ All fields are required")
                return
            
            await create_admin_user(engine, email, username, password, "superadmin")
            
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
        print("\nAdmin Login Endpoint:")
        print("POST /api/v1/admin/auth/login")
        print("\nTest with:")
        print(f'curl -X POST "http://localhost:8000/api/v1/admin/auth/login" \\')
        print('  -H "Content-Type: application/json" \\')
        print(f'  -d \'{{"email":"{email if choice in ["1","2"] else "admin@example.com"}","password":"yourpassword"}}\'')
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
