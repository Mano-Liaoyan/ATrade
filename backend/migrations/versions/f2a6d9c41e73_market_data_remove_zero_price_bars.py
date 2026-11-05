"""market_data: remove the Databento bars with price 0 (market_data.md section 8.8.2)

Revision ID: f2a6d9c41e73
Revises: c4e8a1f7b2d6
"""

from alembic import op

revision = "f2a6d9c41e73"
down_revision = "c4e8a1f7b2d6"


def upgrade() -> None:
    op.execute("""
    CREATE TEMPORARY TABLE zero_price_instrument ON COMMIT DROP AS
        SELECT DISTINCT symbol, exchange, currency FROM databento_bar WHERE close <= 0;

    DELETE FROM databento_bar WHERE close <= 0;

    ALTER TABLE databento_bar ADD CONSTRAINT databento_bar_close_is_positive CHECK (close > 0);

    -- The summary of these instruments, with the merge rule and the calculation of daily_bar_summary.py. An instrument
    -- without daily bars has no summary row. The saved ranges stay, so the removed days have no bar and no IBKR read.
    DELETE FROM daily_bar_summary AS summary USING zero_price_instrument AS instrument
    WHERE summary.symbol = instrument.symbol AND summary.exchange = instrument.exchange
        AND summary.currency = instrument.currency;

    INSERT INTO daily_bar_summary (
        symbol, exchange, currency, last_day_start_utc, last_close, average_trading_value_20
    )
    SELECT instrument.symbol, instrument.exchange, instrument.currency,
        max(merged.start_utc), (array_agg(merged.close ORDER BY merged.start_utc DESC))[1],
        CASE WHEN count(*) = 20 THEN avg(merged.close * merged.volume)::double precision END
    FROM zero_price_instrument AS instrument
        CROSS JOIN (SELECT bar_sources FROM source_order) AS global_order
        CROSS JOIN LATERAL (
            SELECT source_bar.start_utc, source_bar.close, source_bar.volume
            FROM (
                SELECT bar.start_utc, bar.close, bar.volume
                FROM databento_bar AS bar
                WHERE bar.symbol = instrument.symbol AND bar.exchange = instrument.exchange
                    AND bar.currency = instrument.currency AND bar.bar_period = '1-DAY'
                    AND EXISTS (
                        SELECT 1 FROM databento_bar_saved_range AS saved_range
                        WHERE saved_range.symbol = bar.symbol AND saved_range.exchange = bar.exchange
                            AND saved_range.currency = bar.currency AND saved_range.bar_period = bar.bar_period
                            AND saved_range.start_utc <= bar.start_utc AND saved_range.end_utc > bar.start_utc
                    )
                    AND NOT (
                        array_position(global_order.bar_sources, 'ibkr')
                            < array_position(global_order.bar_sources, 'databento')
                        AND EXISTS (
                            SELECT 1 FROM ibkr_bar_saved_range AS saved_range
                            WHERE saved_range.symbol = bar.symbol AND saved_range.exchange = bar.exchange
                                AND saved_range.currency = bar.currency AND saved_range.bar_period = bar.bar_period
                                AND saved_range.start_utc <= bar.start_utc AND saved_range.end_utc > bar.start_utc
                        )
                    )
                UNION ALL
                SELECT bar.start_utc, bar.close, bar.volume
                FROM ibkr_bar AS bar
                WHERE bar.symbol = instrument.symbol AND bar.exchange = instrument.exchange
                    AND bar.currency = instrument.currency AND bar.bar_period = '1-DAY'
                    AND EXISTS (
                        SELECT 1 FROM ibkr_bar_saved_range AS saved_range
                        WHERE saved_range.symbol = bar.symbol AND saved_range.exchange = bar.exchange
                            AND saved_range.currency = bar.currency AND saved_range.bar_period = bar.bar_period
                            AND saved_range.start_utc <= bar.start_utc AND saved_range.end_utc > bar.start_utc
                    )
                    AND NOT (
                        array_position(global_order.bar_sources, 'databento')
                            < array_position(global_order.bar_sources, 'ibkr')
                        AND EXISTS (
                            SELECT 1 FROM databento_bar_saved_range AS saved_range
                            WHERE saved_range.symbol = bar.symbol AND saved_range.exchange = bar.exchange
                                AND saved_range.currency = bar.currency AND saved_range.bar_period = bar.bar_period
                                AND saved_range.start_utc <= bar.start_utc AND saved_range.end_utc > bar.start_utc
                        )
                    )
            ) AS source_bar
            ORDER BY source_bar.start_utc DESC
            LIMIT 20
        ) AS merged
    GROUP BY instrument.symbol, instrument.exchange, instrument.currency;
    """)


def downgrade() -> None:
    # A new import of the DBN files does not bring the removed bars back: the import skips them.
    op.execute("ALTER TABLE databento_bar DROP CONSTRAINT databento_bar_close_is_positive;")
