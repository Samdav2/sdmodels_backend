-- Add tax fields to user_profiles table
ALTER TABLE user_profiles 
ADD COLUMN IF NOT EXISTS tax_id VARCHAR(50),
ADD COLUMN IF NOT EXISTS business_name VARCHAR(255);

-- Create payment_methods table
CREATE TABLE IF NOT EXISTS payment_methods (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE,
    
    -- PayPal
    paypal_email VARCHAR(255),
    
    -- Bank Account
    account_holder_name VARCHAR(255),
    account_number_last_four VARCHAR(4),
    routing_number VARCHAR(50),
    bank_name VARCHAR(255),
    
    -- Stripe
    stripe_account_id VARCHAR(255),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_payment_methods_user_id 
ON payment_methods(user_id);

CREATE INDEX IF NOT EXISTS idx_payment_methods_is_primary 
ON payment_methods(is_primary);
