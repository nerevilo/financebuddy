"""Add insights goals income profile tables

Revision ID: 0295cc479611
Revises: 2f4146a909e9
Create Date: 2026-01-12 16:57:18.827359

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0295cc479611'
down_revision: Union[str, Sequence[str], None] = '2f4146a909e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. user_profiles (FK -> users)
    op.create_table('user_profiles',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('monthly_income_estimate', sa.Float(), nullable=True),
        sa.Column('income_last_calculated', sa.DateTime(), nullable=True),
        sa.Column('household_size', sa.Integer(), nullable=True, default=1),
        sa.Column('location_city', sa.String(), nullable=True),
        sa.Column('location_state', sa.String(), nullable=True),
        sa.Column('context_notes', sa.Text(), nullable=True),
        sa.Column('insight_frequency', sa.String(), nullable=True, default='daily'),
        sa.Column('preferred_categories', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )

    # 2. goals (FK -> users)
    op.create_table('goals',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('target_amount', sa.Float(), nullable=False),
        sa.Column('current_amount', sa.Float(), nullable=True, default=0.0),
        sa.Column('monthly_allocation', sa.Float(), nullable=True),
        sa.Column('deadline', sa.Date(), nullable=True),
        sa.Column('priority', sa.String(), nullable=True, default='medium'),
        sa.Column('status', sa.String(), nullable=True, default='active'),
        sa.Column('auto_suggested', sa.Boolean(), nullable=True, default=False),
        sa.Column('suggestion_reason', sa.Text(), nullable=True),
        sa.Column('related_category', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_goals_user_status', 'goals', ['user_id', 'status'])

    # 3. income_sources (FK -> users, transactions)
    op.create_table('income_sources',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('frequency', sa.String(), nullable=False),
        sa.Column('auto_detected', sa.Boolean(), nullable=True, default=False),
        sa.Column('detection_pattern', sa.String(), nullable=True),
        sa.Column('last_transaction_id', sa.String(), nullable=True),
        sa.Column('next_expected_date', sa.Date(), nullable=True),
        sa.Column('last_received_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['last_transaction_id'], ['transactions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_income_sources_user', 'income_sources', ['user_id'])

    # 4. insights (FK -> users)
    op.create_table('insights',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('action', sa.Text(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('amount_referenced', sa.Float(), nullable=True),
        sa.Column('comparison_period', sa.String(), nullable=True),
        sa.Column('priority_score', sa.Float(), nullable=True, default=0.5),
        sa.Column('emoji', sa.String(), nullable=True),
        sa.Column('feedback', sa.String(), nullable=True, default='none'),
        sa.Column('feedback_at', sa.DateTime(), nullable=True),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
        sa.Column('llm_source', sa.String(), nullable=True),
        sa.Column('generation_cost', sa.Float(), nullable=True, default=0.0),
        sa.Column('prompt_version', sa.String(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=True, default=False),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_insights_user_generated', 'insights', ['user_id', 'generated_at'])
    op.create_index('ix_insights_type', 'insights', ['type'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_insights_type', 'insights')
    op.drop_index('ix_insights_user_generated', 'insights')
    op.drop_table('insights')
    op.drop_index('ix_income_sources_user', 'income_sources')
    op.drop_table('income_sources')
    op.drop_index('ix_goals_user_status', 'goals')
    op.drop_table('goals')
    op.drop_table('user_profiles')
