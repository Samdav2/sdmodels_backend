-- Admin Users Table (Separate from regular users)
-- Run this script to create the admin authentication system

-- Create admin_users table
CREATE TABLE IF NOT EXISTS admin_users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(20) DEFAULT 'admin' NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    avatar_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_login TIMESTAMP,
    
    -- Permissions
    can_manage_users BOOLEAN DEFAULT TRUE NOT NULL,
    can_manage_bounties BOOLEAN DEFAULT TRUE NOT NULL,
    can_manage_content BOOLEAN DEFAULT TRUE NOT NULL,
    can_manage_settings BOOLEAN DEFAULT TRUE NOT NULL,
    can_view_analytics BOOLEAN DEFAULT TRUE NOT NULL
);

-- Create indexes
CREATE INDEX IF NOT EXISTS ix_admin_users_id ON admin_users(id);
CREATE INDEX IF NOT EXISTS ix_admin_users_email ON admin_users(email);
CREATE INDEX IF NOT EXISTS ix_admin_users_username ON admin_users(username);
CREATE INDEX IF NOT EXISTS ix_admin_users_is_active ON admin_users(is_active);

-- Verify table was created
SELECT 
    'admin_users' as table_name, 
    COUNT(*) as row_count 
FROM admin_users;

-- Success message
SELECT '✅ Admin users table created successfully!' as status;
SELECT 'Run: python scripts/setup_admin_system.py to create your first admin' as next_step;
