"""
Database Migration for Password Reset Tokens

Create the password_reset_tokens table required by Phase 4.

Options:
1. Raw SQL (PostgreSQL)
2. SQLAlchemy programmatic
3. Alembic migration (if using Alembic)
"""

# ============================================================================
# OPTION 1: Raw SQL (PostgreSQL)
# ============================================================================
# Run this directly in your PostgreSQL database or through your DB client

SQL_MIGRATION = """
-- Create password_reset_tokens table
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token 
    ON password_reset_tokens(token);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user_id 
    ON password_reset_tokens(user_id);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user_id_unused
    ON password_reset_tokens(user_id, used_at) 
    WHERE used_at IS NULL;
"""

# ============================================================================
# OPTION 2: SQLAlchemy Programmatic (Run in your app startup)
# ============================================================================

async def create_password_reset_tables():
    """
    Create password_reset_tokens table using SQLAlchemy.
    
    Add this to your app initialization:
    
    from eden.db import get_db
    from eden.auth.password_reset import PasswordResetToken
    import sqlalchemy as sa
    
    async def startup():
        # Create table if it doesn't exist
        async with get_db() as session:
            await session.run_sync(
                PasswordResetToken.__table__.create,
                bind=session.get_bind(),
                checkfirst=True
            )
    
    Or in alembic/env.py or during initial setup:
    """
    pass


# ============================================================================
# OPTION 3: Alembic Migration (if you're using Alembic)
# ============================================================================

ALEMBIC_MIGRATION_DOWN = """
# AlembicMigration: Create password_reset_tokens table

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    '''Create password_reset_tokens table'''
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), 
                  server_default=sa.text('gen_random_uuid()'), 
                  nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), 
                  nullable=False),
        sa.Column('token', sa.String(255), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), 
                  server_default=sa.text('CURRENT_TIMESTAMP'), 
                  nullable=True),
        sa.Column('updated_at', sa.DateTime(), 
                  server_default=sa.text('CURRENT_TIMESTAMP'), 
                  nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], 
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token', name='uq_token')
    )
    
    # Create indexes
    op.create_index('idx_password_reset_tokens_token', 
                    'password_reset_tokens', ['token'])
    op.create_index('idx_password_reset_tokens_user_id', 
                    'password_reset_tokens', ['user_id'])
    op.create_index('idx_password_reset_tokens_user_id_unused', 
                    'password_reset_tokens', 
                    ['user_id', 'used_at'],
                    postgresql_where=sa.text('used_at IS NULL'))


def downgrade():
    '''Drop password_reset_tokens table'''
    op.drop_table('password_reset_tokens')
"""

# ============================================================================
# QUICK START: Choose Your Method
# ============================================================================

if __name__ == "__main__":
    print("""
    PASSWORD RESET TOKENS - DATABASE MIGRATION
    
    Choose one of the following:
    
    1. RAW SQL (Recommended if using psql directly):
       - Copy the SQL_MIGRATION above
       - Run in your PostgreSQL client
       - Takes ~10 seconds
    
    2. SQLAlchemy (Recommended if using Eden):
       - Add the create_password_reset_tables() call to app startup
       - Run app once to create table
       - Tables auto-created if they don't exist
    
    3. Alembic (Recommended for production):
       - Create file: alembic/versions/XXX_add_password_reset_tokens.py
       - Paste ALEMBIC_MIGRATION_DOWN code
       - Run: alembic upgrade head
    
    ============================================================
    FASTEST METHOD: Raw SQL + psql
    ============================================================
    
    $ psql -U your_user -d your_database
    
    password_reset_db=# CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        token VARCHAR(255) NOT NULL UNIQUE,
        expires_at TIMESTAMP NOT NULL,
        used_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    password_reset_db=# CREATE INDEX idx_password_reset_tokens_token 
                        ON password_reset_tokens(token);
    
    password_reset_db=# \\d password_reset_tokens
    
    This command shows you the table structure to verify it was created.
    """)
