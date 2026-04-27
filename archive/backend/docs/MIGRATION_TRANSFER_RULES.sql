-- Migration: Add transfer_rules table for user-configurable rules
-- Created: 2026-01-07
-- Purpose: Allow users to add custom transfer detection rules without code changes

-- Create transfer_rules table
CREATE TABLE IF NOT EXISTS transfer_rules (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR REFERENCES users(id) ON DELETE CASCADE,  -- NULL = global rule
    rule_type VARCHAR NOT NULL CHECK (rule_type IN ('internal_transfer', 'payment', 'exclude')),
    pattern VARCHAR NOT NULL,
    is_regex BOOLEAN DEFAULT FALSE,
    priority REAL DEFAULT 0.0,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_transfer_rules_user ON transfer_rules(user_id);
CREATE INDEX idx_transfer_rules_active ON transfer_rules(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_transfer_rules_priority ON transfer_rules(priority DESC);

-- Example: Add a global rule for a common credit card
INSERT INTO transfer_rules (
    id,
    user_id,
    rule_type,
    pattern,
    is_regex,
    priority,
    description
) VALUES (
    '00000000-0000-0000-0000-000000000001',
    NULL,  -- Global rule
    'payment',
    'VENMO CREDIT CARD',
    FALSE,
    5.0,
    'Venmo credit card payments should not count as spending'
);

-- Example: Add a user-specific rule
-- INSERT INTO transfer_rules (
--     id,
--     user_id,
--     rule_type,
--     pattern,
--     is_regex,
--     priority,
--     description
-- ) VALUES (
--     '00000000-0000-0000-0000-000000000002',
--     'your-user-id-here',
--     'internal_transfer',
--     'MY ROOMMATE VENMO',
--     FALSE,
--     10.0,
--     'Roommate rent splits via Venmo are transfers, not spending'
-- );

-- Example: Add a regex-based rule
-- INSERT INTO transfer_rules (
--     id,
--     user_id,
--     rule_type,
--     pattern,
--     is_regex,
--     priority,
--     description
-- ) VALUES (
--     '00000000-0000-0000-0000-000000000003',
--     NULL,
--     'internal_transfer',
--     'XFER.*TO.*[0-9]{4}',  -- Matches "XFER TO ...1234"
--     TRUE,
--     3.0,
--     'Pattern matching for transfers with account numbers'
-- );
