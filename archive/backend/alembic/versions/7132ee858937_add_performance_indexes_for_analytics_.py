"""Add performance indexes for analytics queries

Revision ID: 7132ee858937
Revises: d4e5f6g7h8i9
Create Date: 2026-01-15 12:40:11.414386

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7132ee858937'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6g7h8i9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add performance indexes for analytics queries."""
    # Institution composite index for user + status filtering
    op.create_index('ix_institutions_user_status', 'institutions', ['user_id', 'status'], unique=False)

    # Transaction indexes for category/transfer filtering and aggregation
    op.create_index('ix_transactions_enriched_category', 'transactions', ['enriched_category'], unique=False)
    op.create_index('ix_transactions_is_transfer', 'transactions', ['is_transfer'], unique=False)
    op.create_index('ix_transactions_merchant_name', 'transactions', ['merchant_name'], unique=False)
    op.create_index('ix_transactions_teller_category', 'transactions', ['teller_category'], unique=False)


def downgrade() -> None:
    """Remove performance indexes."""
    op.drop_index('ix_transactions_teller_category', table_name='transactions')
    op.drop_index('ix_transactions_merchant_name', table_name='transactions')
    op.drop_index('ix_transactions_is_transfer', table_name='transactions')
    op.drop_index('ix_transactions_enriched_category', table_name='transactions')
    op.drop_index('ix_institutions_user_status', table_name='institutions')
