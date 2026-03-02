#!/usr/bin/env python3
"""
Check if users have models in the database
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()


async def check_user_models():
    db_url = os.getenv('DATABASE_URL', 'postgresql+asyncpg://sdmodels:sdmodels@localhost:5432/sdmodels')
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    
    conn = await asyncpg.connect(db_url)
    
    try:
        # Get all users
        users = await conn.fetch("""
            SELECT id, username, email, user_type
            FROM users
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        print("=" * 80)
        print("CHECKING USER MODELS")
        print("=" * 80)
        
        for user in users:
            user_id = user['id']
            username = user['username']
            user_type = user['user_type']
            
            # Count models for this user
            model_count = await conn.fetchval("""
                SELECT COUNT(*)
                FROM models
                WHERE creator_id = $1
            """, user_id)
            
            print(f"\n👤 User: {username} ({user_type})")
            print(f"   ID: {user_id}")
            print(f"   📦 Models: {model_count}")
            
            if model_count > 0:
                # Get model details
                models = await conn.fetch("""
                    SELECT id, title, status, created_at
                    FROM models
                    WHERE creator_id = $1
                    ORDER BY created_at DESC
                    LIMIT 5
                """, user_id)
                
                for model in models:
                    print(f"      - {model['title']} (Status: {model['status']}, ID: {model['id']})")
        
        # Overall stats
        print("\n" + "=" * 80)
        print("OVERALL STATISTICS")
        print("=" * 80)
        
        total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
        total_models = await conn.fetchval("SELECT COUNT(*) FROM models")
        creators_with_models = await conn.fetchval("""
            SELECT COUNT(DISTINCT creator_id) FROM models
        """)
        
        print(f"Total Users: {total_users}")
        print(f"Total Models: {total_models}")
        print(f"Creators with Models: {creators_with_models}")
        
        # Check if creator_id types match
        print("\n" + "=" * 80)
        print("TYPE VERIFICATION")
        print("=" * 80)
        
        user_id_type = await conn.fetchval("""
            SELECT data_type
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'id'
        """)
        
        model_creator_id_type = await conn.fetchval("""
            SELECT data_type
            FROM information_schema.columns
            WHERE table_name = 'models' AND column_name = 'creator_id'
        """)
        
        print(f"users.id type: {user_id_type}")
        print(f"models.creator_id type: {model_creator_id_type}")
        
        if user_id_type == model_creator_id_type:
            print("✅ Types match!")
        else:
            print("❌ TYPE MISMATCH! This will cause query failures!")
        
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(check_user_models())
