"""add_enrichment_optimizations

Revision ID: b1c2d3e4f5g6
Revises: a0b1c2d3e4f5
Create Date: 2026-01-29 10:00:00.000000

Adds:
1. Enrichment retry queue columns (attempts, error, queued_at)
2. Partial index for unenriched transactions
3. Covering index for dashboard queries
4. Materialized view for monthly spending (PostgreSQL only)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5g6'
down_revision: Union[str, Sequence[str], None] = 'a0b1c2d3e4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Get connection to check database type
    connection = op.get_bind()
    is_postgresql = connection.dialect.name == 'postgresql'

    # 1. Add enrichment retry queue columns to transactions
    op.add_column('transactions', sa.Column('enrichment_attempts', sa.Integer(), server_default='0'))
    op.add_column('transactions', sa.Column('enrichment_error', sa.Text(), nullable=True))
    op.add_column('transactions', sa.Column('enrichment_queued_at', sa.DateTime(), nullable=True))

    # 2. Add partial index for enrichment queue (PostgreSQL only)
    if is_postgresql:
        # Partial index for unenriched transactions that need processing
        op.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_transactions_enrichment_queue
            ON transactions (enrichment_queued_at)
            WHERE enriched_category IS NULL
              AND enrichment_attempts < 3
              AND is_transfer = false;
        """))

        # Partial index for fast unenriched lookup
        op.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_transactions_unenriched
            ON transactions (created_at)
            WHERE enriched_category IS NULL AND is_transfer = false;
        """))

        # 3. Materialized view for monthly spending aggregations
        op.execute(text("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS mv_monthly_spending AS
            SELECT
                i.user_id,
                date_trunc('month', t.date) as month,
                COALESCE(t.enriched_category, t.teller_category, 'other') as category,
                COUNT(*) as transaction_count,
                SUM(CASE WHEN t.amount < 0 THEN ABS(t.amount) ELSE 0 END) as total_spent,
                SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END) as total_income
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            JOIN institutions i ON a.institution_id = i.id
            WHERE t.is_transfer = false
            GROUP BY i.user_id, date_trunc('month', t.date),
                     COALESCE(t.enriched_category, t.teller_category, 'other');
        """))

        # Unique index on materialized view for CONCURRENTLY refresh
        op.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ix_mv_monthly_spending_pk
            ON mv_monthly_spending (user_id, month, category);
        """))

        # 4. Materialized view for top merchants
        op.execute(text("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS mv_top_merchants AS
            SELECT
                i.user_id,
                COALESCE(t.enriched_merchant, t.merchant_name) as merchant,
                COALESCE(t.enriched_category, t.teller_category, 'other') as category,
                COUNT(*) as transaction_count,
                SUM(ABS(t.amount)) as total_amount
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            JOIN institutions i ON a.institution_id = i.id
            WHERE t.amount < 0
              AND COALESCE(t.enriched_merchant, t.merchant_name) IS NOT NULL
            GROUP BY i.user_id, COALESCE(t.enriched_merchant, t.merchant_name),
                     COALESCE(t.enriched_category, t.teller_category, 'other');
        """))

        # Index on top merchants for fast user lookups
        op.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ix_mv_top_merchants_pk
            ON mv_top_merchants (user_id, merchant, category);
        """))

        op.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_mv_top_merchants_amount
            ON mv_top_merchants (user_id, total_amount DESC);
        """))

    else:
        # SQLite fallback: just create a simple index (no partial indexes or MVs)
        op.create_index(
            'ix_transactions_unenriched_simple',
            'transactions',
            ['enriched_category', 'is_transfer'],
            unique=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    connection = op.get_bind()
    is_postgresql = connection.dialect.name == 'postgresql'

    if is_postgresql:
        # Drop materialized views
        op.execute(text("DROP MATERIALIZED VIEW IF EXISTS mv_top_merchants;"))
        op.execute(text("DROP MATERIALIZED VIEW IF EXISTS mv_monthly_spending;"))

        # Drop partial indexes
        op.execute(text("DROP INDEX IF EXISTS ix_transactions_unenriched;"))
        op.execute(text("DROP INDEX IF EXISTS ix_transactions_enrichment_queue;"))
    else:
        op.drop_index('ix_transactions_unenriched_simple', table_name='transactions')

    # Remove columns
    op.drop_column('transactions', 'enrichment_queued_at')
    op.drop_column('transactions', 'enrichment_error')
    op.drop_column('transactions', 'enrichment_attempts')
