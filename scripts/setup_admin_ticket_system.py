"""
Setup Admin Ticket Management System

This script creates the necessary database tables and columns
for the admin ticket management system.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.session import engine


async def setup_admin_ticket_system():
    """Create tables and columns for admin ticket system"""
    
    async with engine.begin() as conn:
        print("Setting up Admin Ticket Management System...")
        print("-" * 50)
        
        # 1. Add columns to support_tickets table
        print("\n1. Adding columns to support_tickets table...")
        
        columns_to_add = [
            ("tags", "TEXT[]"),
            ("first_response_at", "TIMESTAMP"),
            ("sla_breach", "BOOLEAN DEFAULT FALSE"),
            ("satisfaction_rating", "INTEGER"),
            ("satisfaction_comment", "TEXT"),
            ("closed_at", "TIMESTAMP")
        ]
        
        for column_name, column_type in columns_to_add:
            try:
                await conn.execute(text(f"""
                    ALTER TABLE support_tickets 
                    ADD COLUMN IF NOT EXISTS {column_name} {column_type}
                """))
                print(f"   ✅ Added column: {column_name}")
            except Exception as e:
                print(f"   ⚠️  Column {column_name} might already exist: {e}")
        
        # 2. Add is_internal column to support_messages table
        print("\n2. Adding is_internal column to support_messages table...")
        try:
            await conn.execute(text("""
                ALTER TABLE support_messages 
                ADD COLUMN IF NOT EXISTS is_internal BOOLEAN DEFAULT FALSE
            """))
            print("   ✅ Added column: is_internal")
        except Exception as e:
            print(f"   ⚠️  Column might already exist: {e}")
        
        # 3. Create support_ticket_history table
        print("\n3. Creating support_ticket_history table...")
        try:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS support_ticket_history (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    ticket_id UUID NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
                    admin_id UUID NOT NULL REFERENCES users(id),
                    action VARCHAR(50) NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            print("   ✅ Created table: support_ticket_history")
            
            # Create index
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_history_ticket_id 
                ON support_ticket_history(ticket_id)
            """))
            print("   ✅ Created index: idx_history_ticket_id")
        except Exception as e:
            print(f"   ⚠️  Table might already exist: {e}")
        
        # 4. Create support_canned_responses table
        print("\n4. Creating support_canned_responses table...")
        try:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS support_canned_responses (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    title VARCHAR(100) NOT NULL,
                    content TEXT NOT NULL,
                    category VARCHAR(50),
                    shortcut VARCHAR(20) UNIQUE,
                    usage_count INTEGER DEFAULT 0,
                    created_by UUID REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            print("   ✅ Created table: support_canned_responses")
        except Exception as e:
            print(f"   ⚠️  Table might already exist: {e}")
        
        # 5. Create indexes for performance
        print("\n5. Creating indexes for performance...")
        
        indexes = [
            ("idx_tickets_status", "support_tickets", "status"),
            ("idx_tickets_assigned_to", "support_tickets", "assigned_to"),
            ("idx_tickets_category", "support_tickets", "category"),
            ("idx_tickets_priority", "support_tickets", "priority"),
            ("idx_tickets_created_at", "support_tickets", "created_at DESC"),
            ("idx_tickets_user_id", "support_tickets", "user_id"),
            ("idx_messages_ticket_id", "support_messages", "ticket_id"),
            ("idx_messages_sender_id", "support_messages", "sender_id")
        ]
        
        for index_name, table_name, column in indexes:
            try:
                await conn.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS {index_name} 
                    ON {table_name}({column})
                """))
                print(f"   ✅ Created index: {index_name}")
            except Exception as e:
                print(f"   ⚠️  Index {index_name} might already exist: {e}")
        
        # 6. Insert sample canned responses
        print("\n6. Inserting sample canned responses...")
        
        sample_responses = [
            {
                "title": "Payment Issue - Standard Response",
                "content": "Thank you for contacting us about your payment issue. We are investigating this matter and will resolve it within 24 hours. If you have any additional information, please share it with us.",
                "category": "Payment",
                "shortcut": "/payment"
            },
            {
                "title": "Technical Issue - Initial Response",
                "content": "Thank you for reporting this technical issue. Our technical team is investigating the problem. We will update you as soon as we have more information.",
                "category": "Technical",
                "shortcut": "/tech"
            },
            {
                "title": "Account Issue - Verification",
                "content": "Thank you for contacting us about your account. To verify your identity and assist you better, please provide your registered email address and username.",
                "category": "Account",
                "shortcut": "/account"
            },
            {
                "title": "Refund Request - Processing",
                "content": "We have received your refund request. Our team is reviewing it and will process it within 3-5 business days. You will receive a confirmation email once the refund is processed.",
                "category": "Refund",
                "shortcut": "/refund"
            },
            {
                "title": "Issue Resolved",
                "content": "We are glad to inform you that your issue has been resolved. If you experience any further problems or have additional questions, please don't hesitate to contact us again.",
                "category": "General",
                "shortcut": "/resolved"
            }
        ]
        
        for response in sample_responses:
            try:
                await conn.execute(text("""
                    INSERT INTO support_canned_responses 
                    (title, content, category, shortcut)
                    VALUES (:title, :content, :category, :shortcut)
                    ON CONFLICT (shortcut) DO NOTHING
                """), response)
                print(f"   ✅ Inserted: {response['title']}")
            except Exception as e:
                print(f"   ⚠️  Response might already exist: {e}")
        
        print("\n" + "=" * 50)
        print("✅ Admin Ticket Management System setup complete!")
        print("=" * 50)
        
        print("\nNext steps:")
        print("1. Register routes in app/api/v1/api.py")
        print("2. Extend support_repository.py with new methods")
        print("3. Run test suite: python test_admin_ticket_management.py")
        print("\nDocumentation:")
        print("- ADMIN_TICKET_MANAGEMENT_COMPLETE.md")
        print("- ADMIN_TICKET_QUICK_REFERENCE.md")
        print("- ADMIN_TICKET_SYSTEM_SUMMARY.md")


async def verify_setup():
    """Verify that all tables and columns exist"""
    
    async with engine.begin() as conn:
        print("\n" + "=" * 50)
        print("Verifying Setup...")
        print("=" * 50)
        
        # Check support_tickets columns
        print("\n1. Checking support_tickets columns...")
        result = await conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'support_tickets'
            ORDER BY column_name
        """))
        columns = result.fetchall()
        print(f"   Found {len(columns)} columns:")
        for col in columns:
            print(f"   - {col[0]}: {col[1]}")
        
        # Check support_messages columns
        print("\n2. Checking support_messages columns...")
        result = await conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'support_messages'
            ORDER BY column_name
        """))
        columns = result.fetchall()
        print(f"   Found {len(columns)} columns:")
        for col in columns:
            print(f"   - {col[0]}: {col[1]}")
        
        # Check support_ticket_history table
        print("\n3. Checking support_ticket_history table...")
        result = await conn.execute(text("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_name = 'support_ticket_history'
        """))
        exists = result.scalar()
        if exists:
            print("   ✅ Table exists")
        else:
            print("   ❌ Table does not exist")
        
        # Check support_canned_responses table
        print("\n4. Checking support_canned_responses table...")
        result = await conn.execute(text("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_name = 'support_canned_responses'
        """))
        exists = result.scalar()
        if exists:
            print("   ✅ Table exists")
            
            # Count canned responses
            result = await conn.execute(text("""
                SELECT COUNT(*) FROM support_canned_responses
            """))
            count = result.scalar()
            print(f"   Found {count} canned responses")
        else:
            print("   ❌ Table does not exist")
        
        # Check indexes
        print("\n5. Checking indexes...")
        result = await conn.execute(text("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename IN ('support_tickets', 'support_messages', 'support_ticket_history')
            ORDER BY indexname
        """))
        indexes = result.fetchall()
        print(f"   Found {len(indexes)} indexes:")
        for idx in indexes:
            print(f"   - {idx[0]}")
        
        print("\n" + "=" * 50)
        print("✅ Verification complete!")
        print("=" * 50)


async def main():
    """Main function"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        await verify_setup()
    else:
        await setup_admin_ticket_system()
        await verify_setup()


if __name__ == "__main__":
    asyncio.run(main())
