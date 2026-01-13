"""Add database indexes for performance optimization

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-01-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6g7h8i9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6g7h8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add indexes for frequently queried columns and foreign keys."""
    # Foreign key indexes
    op.create_index('ix_institutions_user_id', 'institutions', ['user_id'])
    op.create_index('ix_accounts_institution_id', 'accounts', ['institution_id'])
    op.create_index('ix_transactions_account_id', 'transactions', ['account_id'])
    op.create_index('ix_transactions_category_id', 'transactions', ['category_id'])
    op.create_index('ix_income_sources_user_id', 'income_sources', ['user_id'])
    op.create_index('ix_goals_user_id', 'goals', ['user_id'])
    op.create_index('ix_insights_user_id', 'insights', ['user_id'])

    # Frequently queried column indexes on Transaction
    op.create_index('ix_transactions_date', 'transactions', ['date'])
    op.create_index('ix_transactions_is_anomaly', 'transactions', ['is_anomaly'])
    op.create_index('ix_transactions_categorization_source', 'transactions', ['categorization_source'])

    # Composite index for common query pattern (account + date filtering)
    op.create_index('ix_transactions_account_id_date', 'transactions', ['account_id', 'date'])


def downgrade() -> None:
    """Remove all added indexes."""
    # Drop composite index
    op.drop_index('ix_transactions_account_id_date', table_name='transactions')

    # Drop frequently queried column indexes
    op.drop_index('ix_transactions_categorization_source', table_name='transactions')
    op.drop_index('ix_transactions_is_anomaly', table_name='transactions')
    op.drop_index('ix_transactions_date', table_name='transactions')

    # Drop foreign key indexes
    op.drop_index('ix_insights_user_id', table_name='insights')
    op.drop_index('ix_goals_user_id', table_name='goals')
    op.drop_index('ix_income_sources_user_id', table_name='income_sources')
    op.drop_index('ix_transactions_category_id', table_name='transactions')
    op.drop_index('ix_transactions_account_id', table_name='transactions')
    op.drop_index('ix_accounts_institution_id', table_name='accounts')
    op.drop_index('ix_institutions_user_id', table_name='institutions')
