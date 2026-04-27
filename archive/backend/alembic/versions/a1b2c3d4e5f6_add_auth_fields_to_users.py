"""Add authentication fields to users table

Revision ID: a1b2c3d4e5f6
Revises: 0295cc479611
Create Date: 2026-01-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '0295cc479611'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add password and auth-related columns to users table."""
    # Add hashed_password column (nullable for migration)
    op.add_column('users', sa.Column('hashed_password', sa.String(), nullable=True))

    # Add is_active column with default True
    op.add_column('users', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False))

    # Add updated_at column
    op.add_column('users', sa.Column('updated_at', sa.DateTime(), nullable=True))

    # Create index on email for faster lookups
    op.create_index('ix_users_email', 'users', ['email'], unique=True)


def downgrade() -> None:
    """Remove auth-related columns."""
    op.drop_index('ix_users_email', 'users')
    op.drop_column('users', 'updated_at')
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'hashed_password')
