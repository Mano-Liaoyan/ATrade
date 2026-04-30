namespace ATrade.MarketData.Timescale;

internal static class TimescaleMarketDataSql
{
    public const string SchemaName = "atrade_market_data";
    public const string CandlesTableName = "candles";
    public const string TrendingSnapshotsTableName = "trending_snapshots";
    public const string QualifiedCandlesTableName = SchemaName + "." + CandlesTableName;
    public const string QualifiedTrendingSnapshotsTableName = SchemaName + "." + TrendingSnapshotsTableName;

    public const string Initialize = """
        CREATE EXTENSION IF NOT EXISTS timescaledb;

        CREATE SCHEMA IF NOT EXISTS atrade_market_data;

        CREATE TABLE IF NOT EXISTS atrade_market_data.candles (
            provider text NOT NULL,
            source text NOT NULL,
            provider_symbol_id text NULL,
            symbol text NOT NULL,
            name text NULL,
            exchange text NULL,
            currency text NULL,
            asset_class text NULL,
            timeframe text NOT NULL,
            candle_time_utc timestamptz NOT NULL,
            generated_at_utc timestamptz NOT NULL,
            open numeric(20, 8) NOT NULL,
            high numeric(20, 8) NOT NULL,
            low numeric(20, 8) NOT NULL,
            close numeric(20, 8) NOT NULL,
            volume bigint NOT NULL,
            created_at_utc timestamptz NOT NULL DEFAULT now(),
            updated_at_utc timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT pk_market_data_candles PRIMARY KEY (provider, source, symbol, timeframe, candle_time_utc)
        );

        SELECT create_hypertable('atrade_market_data.candles', 'candle_time_utc', if_not_exists => TRUE);

        CREATE INDEX IF NOT EXISTS ix_market_data_candles_fresh_series
            ON atrade_market_data.candles (provider, source, symbol, timeframe, generated_at_utc DESC, candle_time_utc ASC);

        CREATE INDEX IF NOT EXISTS ix_market_data_candles_provider_symbol_id
            ON atrade_market_data.candles (provider, provider_symbol_id)
            WHERE provider_symbol_id IS NOT NULL;

        CREATE TABLE IF NOT EXISTS atrade_market_data.trending_snapshots (
            provider text NOT NULL,
            source text NOT NULL,
            provider_symbol_id text NULL,
            symbol text NOT NULL,
            name text NULL,
            exchange text NULL,
            currency text NULL,
            asset_class text NULL,
            sector text NULL,
            generated_at_utc timestamptz NOT NULL,
            last_price numeric(20, 8) NOT NULL,
            change_percent numeric(20, 8) NOT NULL,
            score numeric(20, 8) NOT NULL,
            volume_spike numeric(20, 8) NOT NULL,
            price_momentum numeric(20, 8) NOT NULL,
            volatility numeric(20, 8) NOT NULL,
            external_signal numeric(20, 8) NOT NULL,
            reasons jsonb NOT NULL DEFAULT '[]'::jsonb,
            created_at_utc timestamptz NOT NULL DEFAULT now(),
            updated_at_utc timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT pk_market_data_trending_snapshots PRIMARY KEY (provider, source, symbol, generated_at_utc)
        );

        SELECT create_hypertable('atrade_market_data.trending_snapshots', 'generated_at_utc', if_not_exists => TRUE);

        CREATE INDEX IF NOT EXISTS ix_market_data_trending_snapshots_fresh
            ON atrade_market_data.trending_snapshots (provider, source, generated_at_utc DESC, score DESC, symbol ASC);

        CREATE INDEX IF NOT EXISTS ix_market_data_trending_snapshots_provider_symbol_id
            ON atrade_market_data.trending_snapshots (provider, provider_symbol_id)
            WHERE provider_symbol_id IS NOT NULL;
        """;

    public const string UpsertCandle = """
        INSERT INTO atrade_market_data.candles (
            provider,
            source,
            provider_symbol_id,
            symbol,
            name,
            exchange,
            currency,
            asset_class,
            timeframe,
            candle_time_utc,
            generated_at_utc,
            open,
            high,
            low,
            close,
            volume,
            created_at_utc,
            updated_at_utc)
        VALUES (
            @provider,
            @source,
            @provider_symbol_id,
            @symbol,
            @name,
            @exchange,
            @currency,
            @asset_class,
            @timeframe,
            @candle_time_utc,
            @generated_at_utc,
            @open,
            @high,
            @low,
            @close,
            @volume,
            @written_at_utc,
            @written_at_utc)
        ON CONFLICT (provider, source, symbol, timeframe, candle_time_utc) DO UPDATE
            SET provider_symbol_id = COALESCE(EXCLUDED.provider_symbol_id, atrade_market_data.candles.provider_symbol_id),
                name = COALESCE(EXCLUDED.name, atrade_market_data.candles.name),
                exchange = COALESCE(EXCLUDED.exchange, atrade_market_data.candles.exchange),
                currency = COALESCE(EXCLUDED.currency, atrade_market_data.candles.currency),
                asset_class = COALESCE(EXCLUDED.asset_class, atrade_market_data.candles.asset_class),
                generated_at_utc = EXCLUDED.generated_at_utc,
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume,
                updated_at_utc = EXCLUDED.updated_at_utc;
        """;

    public const string SelectFreshCandles = """
        SELECT provider,
               source,
               provider_symbol_id,
               symbol,
               name,
               exchange,
               currency,
               asset_class,
               timeframe,
               candle_time_utc,
               generated_at_utc,
               open,
               high,
               low,
               close,
               volume
          FROM atrade_market_data.candles
         WHERE provider = @provider
           AND source = @source
           AND symbol = @symbol
           AND timeframe = @timeframe
           AND generated_at_utc >= @freshness_cutoff_utc
         ORDER BY candle_time_utc ASC;
        """;

    public const string UpsertTrendingSnapshotSymbol = """
        INSERT INTO atrade_market_data.trending_snapshots (
            provider,
            source,
            provider_symbol_id,
            symbol,
            name,
            exchange,
            currency,
            asset_class,
            sector,
            generated_at_utc,
            last_price,
            change_percent,
            score,
            volume_spike,
            price_momentum,
            volatility,
            external_signal,
            reasons,
            created_at_utc,
            updated_at_utc)
        VALUES (
            @provider,
            @source,
            @provider_symbol_id,
            @symbol,
            @name,
            @exchange,
            @currency,
            @asset_class,
            @sector,
            @generated_at_utc,
            @last_price,
            @change_percent,
            @score,
            @volume_spike,
            @price_momentum,
            @volatility,
            @external_signal,
            @reasons,
            @written_at_utc,
            @written_at_utc)
        ON CONFLICT (provider, source, symbol, generated_at_utc) DO UPDATE
            SET provider_symbol_id = COALESCE(EXCLUDED.provider_symbol_id, atrade_market_data.trending_snapshots.provider_symbol_id),
                name = COALESCE(EXCLUDED.name, atrade_market_data.trending_snapshots.name),
                exchange = COALESCE(EXCLUDED.exchange, atrade_market_data.trending_snapshots.exchange),
                currency = COALESCE(EXCLUDED.currency, atrade_market_data.trending_snapshots.currency),
                asset_class = COALESCE(EXCLUDED.asset_class, atrade_market_data.trending_snapshots.asset_class),
                sector = COALESCE(EXCLUDED.sector, atrade_market_data.trending_snapshots.sector),
                last_price = EXCLUDED.last_price,
                change_percent = EXCLUDED.change_percent,
                score = EXCLUDED.score,
                volume_spike = EXCLUDED.volume_spike,
                price_momentum = EXCLUDED.price_momentum,
                volatility = EXCLUDED.volatility,
                external_signal = EXCLUDED.external_signal,
                reasons = EXCLUDED.reasons,
                updated_at_utc = EXCLUDED.updated_at_utc;
        """;

    public const string SelectFreshTrendingSnapshot = """
        WITH latest_snapshot AS (
            SELECT generated_at_utc
              FROM atrade_market_data.trending_snapshots
             WHERE provider = @provider
               AND source = @source
               AND generated_at_utc >= @freshness_cutoff_utc
               AND (@symbol IS NULL OR symbol = @symbol)
             ORDER BY generated_at_utc DESC
             LIMIT 1
        )
        SELECT snapshot.provider,
               snapshot.source,
               snapshot.provider_symbol_id,
               snapshot.symbol,
               snapshot.name,
               snapshot.exchange,
               snapshot.currency,
               snapshot.asset_class,
               snapshot.sector,
               snapshot.generated_at_utc,
               snapshot.last_price,
               snapshot.change_percent,
               snapshot.score,
               snapshot.volume_spike,
               snapshot.price_momentum,
               snapshot.volatility,
               snapshot.external_signal,
               snapshot.reasons
          FROM atrade_market_data.trending_snapshots snapshot
          JOIN latest_snapshot
            ON snapshot.generated_at_utc = latest_snapshot.generated_at_utc
         WHERE snapshot.provider = @provider
           AND snapshot.source = @source
           AND (@symbol IS NULL OR snapshot.symbol = @symbol)
         ORDER BY snapshot.score DESC, snapshot.symbol ASC;
        """;
}

