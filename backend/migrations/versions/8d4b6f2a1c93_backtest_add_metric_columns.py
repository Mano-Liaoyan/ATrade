"""backtest: add the metric columns of docs/architecture/backtest.md section 10.9.2

Revision ID: 8d4b6f2a1c93
Revises: 8d4b1e7c2a90
"""

from alembic import op

revision = "8d4b6f2a1c93"
down_revision = "8d4b1e7c2a90"


def upgrade() -> None:
    op.execute("""
    -- Null until the backtest finishes, and null when a metric has no meaning (section 10.9.3).
    -- Backtests that finished before this migration keep null.
    ALTER TABLE backtest
        ADD COLUMN cagr_percent numeric,
        ADD COLUMN annual_volatility_percent numeric,
        ADD COLUMN sharpe_ratio numeric,
        ADD COLUMN sortino_ratio numeric,
        ADD COLUMN calmar_ratio numeric,
        ADD COLUMN profit_factor numeric,
        ADD COLUMN average_win_usd numeric,
        ADD COLUMN average_win_percent numeric,
        ADD COLUMN average_loss_usd numeric,
        ADD COLUMN exposure_percent numeric,
        ADD COLUMN turnover_per_year numeric,
        ADD COLUMN win_rate_percent numeric;
    """)


def downgrade() -> None:
    op.execute("""
    ALTER TABLE backtest
        DROP COLUMN cagr_percent,
        DROP COLUMN annual_volatility_percent,
        DROP COLUMN sharpe_ratio,
        DROP COLUMN sortino_ratio,
        DROP COLUMN calmar_ratio,
        DROP COLUMN profit_factor,
        DROP COLUMN average_win_usd,
        DROP COLUMN average_win_percent,
        DROP COLUMN average_loss_usd,
        DROP COLUMN exposure_percent,
        DROP COLUMN turnover_per_year,
        DROP COLUMN win_rate_percent;
    """)
