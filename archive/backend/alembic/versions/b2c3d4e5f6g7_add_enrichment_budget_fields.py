"""Add enrichment budget fields to users table

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add enrichment budget tracking columns to users table."""
    # Add enrichment_budget column with default $1.00
    op.add_column('users', sa.Column('enrichment_budget', sa.Float(), server_default='1.0', nullable=True))

    # Add enrichment_spent column with default 0
    op.add_column('users', sa.Column('enrichment_spent', sa.Float(), server_default='0.0', nullable=True))

    # Add enrichment_last_reset for future monthly resets
    op.add_column('users', sa.Column('enrichment_last_reset', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove enrichment budget columns."""
    op.drop_column('users', 'enrichment_last_reset')
    op.drop_column('users', 'enrichment_spent')
    op.drop_column('users', 'enrichment_budget')
