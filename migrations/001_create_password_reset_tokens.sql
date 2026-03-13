-- Password Reset Token Table Migration
-- Execute this SQL to create the password_reset_tokens table

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_token (token),
    INDEX idx_user_id_unused (user_id, used_at)
);

-- For PostgreSQL, use:
-- CREATE INDEX IF NOT EXISTS idx_token ON password_reset_tokens(token);
-- CREATE INDEX IF NOT EXISTS idx_user_id_unused ON password_reset_tokens(user_id, used_at);
