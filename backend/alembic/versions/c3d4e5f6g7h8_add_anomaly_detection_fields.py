"""Add anomaly detection and one-time expense fields to transactions

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-01-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add anomaly detection and one-time expense fields to transactions table."""
    # Anomaly Detection Fields (system-populated via statistical analysis)
    op.add_column('transactions', sa.Column('is_anomaly', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('transactions', sa.Column('anomaly_score', sa.Float(), nullable=True))
    op.add_column('transactions', sa.Column('anomaly_reason', sa.String(), nullable=True))

    # User Classification Fields
    op.add_column('transactions', sa.Column('is_one_time', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('transactions', sa.Column('one_time_reason', sa.String(), nullable=True))
    op.add_column('transactions', sa.Column('exclude_from_budget', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('transactions', sa.Column('user_reviewed', sa.Boolean(), server_default='false', nullable=True))

    # Index for efficient querying of unreviewed anomalies
    op.create_index(
        'ix_transactions_unreviewed_anomalies',
        'transactions',
        ['is_anomaly', 'user_reviewed'],
        postgresql_where=sa.text("is_anomaly = true AND user_reviewed = false")
    )


def downgrade() -> None:
    """Remove anomaly detection and one-time expense fields."""
    op.drop_index('ix_transactions_unreviewed_anomalies', table_name='transactions')
    op.drop_column('transactions', 'user_reviewed')
    op.drop_column('transactions', 'exclude_from_budget')
    op.drop_column('transactions', 'one_time_reason')
    op.drop_column('transactions', 'is_one_time')
    op.drop_column('transactions', 'anomaly_reason')
    op.drop_column('transactions', 'anomaly_score')
    op.drop_column('transactions', 'is_anomaly')
