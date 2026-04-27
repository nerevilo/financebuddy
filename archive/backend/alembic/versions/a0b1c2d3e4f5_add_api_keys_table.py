"""add_api_keys_table

Revision ID: a0b1c2d3e4f5
Revises: 9a1b2c3d4e5f
Create Date: 2026-01-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a0b1c2d3e4f5'
down_revision: Union[str, Sequence[str], None] = '9a1b2c3d4e5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'api_keys',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('key_hash', sa.String(), nullable=False),
        sa.Column('key_prefix', sa.String(), nullable=False),
        sa.Column('scopes', sa.Text(), nullable=False, server_default='["*"]'),
        sa.Column('tier', sa.String(), nullable=False, server_default='beta'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_api_keys_user_id', 'api_keys', ['user_id'], unique=False)
    op.create_index('ix_api_keys_user_active', 'api_keys', ['user_id', 'is_active'], unique=False)
    op.create_index('ix_api_keys_key_hash', 'api_keys', ['key_hash'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_api_keys_key_hash', table_name='api_keys')
    op.drop_index('ix_api_keys_user_active', table_name='api_keys')
    op.drop_index('ix_api_keys_user_id', table_name='api_keys')
    op.drop_table('api_keys')
