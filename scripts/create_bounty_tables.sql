-- Bounty System Database Tables
-- Run this script if tables already exist and you want to recreate them

-- Drop existing tables (if they exist)
DROP TABLE IF EXISTS escrow_transactions CASCADE;
DROP TABLE IF EXISTS bounty_submissions CASCADE;
DROP TABLE IF EXISTS bounty_applications CASCADE;
DROP TABLE IF EXISTS bounties CASCADE;

-- Create bounties table
CREATE TABLE bounties (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    budget FLOAT NOT NULL,
    deadline DATE NOT NULL,
    category VARCHAR(100) NOT NULL,
    difficulty VARCHAR(20) NOT NULL,
    status VARCHAR(50) DEFAULT 'open' NOT NULL,
    requirements JSON NOT NULL,
    poster_id INTEGER NOT NULL REFERENCES users(id),
    claimed_by_id INTEGER REFERENCES users(id),
    claimed_at TIMESTAMP,
    submitted_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL,
    CONSTRAINT check_difficulty CHECK (difficulty IN ('easy', 'medium', 'hard')),
    CONSTRAINT check_status CHECK (status IN ('open', 'claimed', 'in_progress', 'submitted', 'completed', 'cancelled'))
);

-- Create indexes for bounties
CREATE INDEX ix_bounties_id ON bounties(id);
CREATE INDEX ix_bounties_status ON bounties(status);
CREATE INDEX ix_bounties_category ON bounties(category);
CREATE INDEX ix_bounties_poster_id ON bounties(poster_id);
CREATE INDEX ix_bounties_claimed_by_id ON bounties(claimed_by_id);

-- Create bounty_applications table
CREATE TABLE bounty_applications (
    id SERIAL PRIMARY KEY,
    bounty_id INTEGER NOT NULL REFERENCES bounties(id) ON DELETE CASCADE,
    applicant_id INTEGER NOT NULL REFERENCES users(id),
    proposal TEXT NOT NULL,
    estimated_delivery DATE NOT NULL,
    portfolio_links JSON,
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    CONSTRAINT check_application_status CHECK (status IN ('pending', 'approved', 'rejected')),
    CONSTRAINT uq_bounty_applicant UNIQUE (bounty_id, applicant_id)
);

-- Create indexes for applications
CREATE INDEX ix_bounty_applications_id ON bounty_applications(id);
CREATE INDEX ix_bounty_applications_bounty_id ON bounty_applications(bounty_id);
CREATE INDEX ix_bounty_applications_applicant_id ON bounty_applications(applicant_id);

-- Create bounty_submissions table
CREATE TABLE bounty_submissions (
    id SERIAL PRIMARY KEY,
    bounty_id INTEGER NOT NULL REFERENCES bounties(id) ON DELETE CASCADE UNIQUE,
    artist_id INTEGER NOT NULL REFERENCES users(id),
    model_url VARCHAR(500) NOT NULL,
    preview_images JSON,
    notes TEXT,
    status VARCHAR(50) DEFAULT 'pending' NOT NULL,
    feedback TEXT,
    submitted_at TIMESTAMP DEFAULT NOW() NOT NULL,
    reviewed_at TIMESTAMP,
    CONSTRAINT check_submission_status CHECK (status IN ('pending', 'approved', 'rejected', 'revision_requested'))
);

-- Create indexes for submissions
CREATE INDEX ix_bounty_submissions_id ON bounty_submissions(id);
CREATE UNIQUE INDEX ix_bounty_submissions_bounty_id ON bounty_submissions(bounty_id);

-- Create escrow_transactions table
CREATE TABLE escrow_transactions (
    id SERIAL PRIMARY KEY,
    bounty_id INTEGER NOT NULL REFERENCES bounties(id),
    buyer_id INTEGER NOT NULL REFERENCES users(id),
    artist_id INTEGER REFERENCES users(id),
    amount FLOAT NOT NULL,
    platform_fee FLOAT NOT NULL,
    status VARCHAR(50) DEFAULT 'held' NOT NULL,
    held_at TIMESTAMP DEFAULT NOW() NOT NULL,
    released_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    CONSTRAINT check_escrow_status CHECK (status IN ('held', 'released', 'refunded'))
);

-- Create indexes for escrow
CREATE INDEX ix_escrow_transactions_id ON escrow_transactions(id);
CREATE INDEX ix_escrow_transactions_bounty_id ON escrow_transactions(bounty_id);

-- Verify tables were created
SELECT 
    'bounties' as table_name, 
    COUNT(*) as row_count 
FROM bounties
UNION ALL
SELECT 
    'bounty_applications' as table_name, 
    COUNT(*) as row_count 
FROM bounty_applications
UNION ALL
SELECT 
    'bounty_submissions' as table_name, 
    COUNT(*) as row_count 
FROM bounty_submissions
UNION ALL
SELECT 
    'escrow_transactions' as table_name, 
    COUNT(*) as row_count 
FROM escrow_transactions;

-- Success message
SELECT '✅ Bounty system tables created successfully!' as status;
