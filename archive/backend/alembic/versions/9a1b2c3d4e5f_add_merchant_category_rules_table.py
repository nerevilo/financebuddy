"""add_merchant_category_rules_table

Revision ID: 9a1b2c3d4e5f
Revises: 8043097fa004
Create Date: 2026-01-15 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a1b2c3d4e5f'
down_revision: Union[str, Sequence[str], None] = '8043097fa004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'merchant_category_rules',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('merchant_name', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('times_applied', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_merchant_category_rules_user_id', 'merchant_category_rules', ['user_id'], unique=False)
    op.create_index('ix_merchant_category_rules_user_merchant', 'merchant_category_rules', ['user_id', 'merchant_name'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_merchant_category_rules_user_merchant', table_name='merchant_category_rules')
    op.drop_index('ix_merchant_category_rules_user_id', table_name='merchant_category_rules')
    op.drop_table('merchant_category_rules')
