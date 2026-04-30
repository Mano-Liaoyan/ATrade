using ATrade.MarketData.Timescale;

namespace ATrade.MarketData.Timescale.Tests;

public sealed class TimescaleMarketDataSqlTests
{
    [Fact]
    public void InitializeCreatesIdempotentTimescaleSchemaForCandlesAndTrendingSnapshots()
    {
        var sql = TimescaleMarketDataSql.Initialize;

        Assert.Contains("CREATE EXTENSION IF NOT EXISTS timescaledb", sql, StringComparison.Ordinal);
        Assert.Contains("CREATE SCHEMA IF NOT EXISTS atrade_market_data", sql, StringComparison.Ordinal);
        Assert.Contains("CREATE TABLE IF NOT EXISTS atrade_market_data.candles", sql, StringComparison.Ordinal);
        Assert.Contains("CREATE TABLE IF NOT EXISTS atrade_market_data.trending_snapshots", sql, StringComparison.Ordinal);
        Assert.Contains("provider text NOT NULL", sql, StringComparison.Ordinal);
        Assert.Contains("source text NOT NULL", sql, StringComparison.Ordinal);
        Assert.Contains("provider_symbol_id text NULL", sql, StringComparison.Ordinal);
        Assert.Contains("symbol text NOT NULL", sql, StringComparison.Ordinal);
        Assert.Contains("exchange text NULL", sql, StringComparison.Ordinal);
        Assert.Contains("currency text NULL", sql, StringComparison.Ordinal);
        Assert.Contains("asset_class text NULL", sql, StringComparison.Ordinal);
        Assert.Contains("timeframe text NOT NULL", sql, StringComparison.Ordinal);
        Assert.Contains("candle_time_utc timestamptz NOT NULL", sql, StringComparison.Ordinal);
        Assert.Contains("generated_at_utc timestamptz NOT NULL", sql, StringComparison.Ordinal);
        Assert.Contains("created_at_utc timestamptz NOT NULL DEFAULT now()", sql, StringComparison.Ordinal);
        Assert.Contains("updated_at_utc timestamptz NOT NULL DEFAULT now()", sql, StringComparison.Ordinal);
        Assert.Contains("SELECT create_hypertable('atrade_market_data.candles', 'candle_time_utc', if_not_exists => TRUE)", sql, StringComparison.Ordinal);
        Assert.Contains("SELECT create_hypertable('atrade_market_data.trending_snapshots', 'generated_at_utc', if_not_exists => TRUE)", sql, StringComparison.Ordinal);
    }

    [Fact]
    public void CandleStatementsUseFreshnessPredicateAndStableConflictKey()
    {
        Assert.Contains("ON CONFLICT (provider, source, symbol, timeframe, candle_time_utc) DO UPDATE", TimescaleMarketDataSql.UpsertCandle, StringComparison.Ordinal);
        Assert.Contains("updated_at_utc = EXCLUDED.updated_at_utc", TimescaleMarketDataSql.UpsertCandle, StringComparison.Ordinal);
        Assert.Contains("WHERE provider = @provider", TimescaleMarketDataSql.SelectFreshCandles, StringComparison.Ordinal);
        Assert.Contains("AND source = @source", TimescaleMarketDataSql.SelectFreshCandles, StringComparison.Ordinal);
        Assert.Contains("AND symbol = @symbol", TimescaleMarketDataSql.SelectFreshCandles, StringComparison.Ordinal);
        Assert.Contains("AND timeframe = @timeframe", TimescaleMarketDataSql.SelectFreshCandles, StringComparison.Ordinal);
        Assert.Contains("AND generated_at_utc >= @freshness_cutoff_utc", TimescaleMarketDataSql.SelectFreshCandles, StringComparison.Ordinal);
        Assert.Contains("ORDER BY candle_time_utc ASC", TimescaleMarketDataSql.SelectFreshCandles, StringComparison.Ordinal);
    }

    [Fact]
    public void TrendingStatementsUseFreshnessPredicateLatestSnapshotAndStableConflictKey()
    {
        Assert.Contains("ON CONFLICT (provider, source, symbol, generated_at_utc) DO UPDATE", TimescaleMarketDataSql.UpsertTrendingSnapshotSymbol, StringComparison.Ordinal);
        Assert.Contains("reasons jsonb NOT NULL DEFAULT '[]'::jsonb", TimescaleMarketDataSql.Initialize, StringComparison.Ordinal);
        Assert.Contains("WITH latest_snapshot AS", TimescaleMarketDataSql.SelectFreshTrendingSnapshot, StringComparison.Ordinal);
        Assert.Contains("AND generated_at_utc >= @freshness_cutoff_utc", TimescaleMarketDataSql.SelectFreshTrendingSnapshot, StringComparison.Ordinal);
        Assert.Contains("AND (@symbol IS NULL OR symbol = @symbol)", TimescaleMarketDataSql.SelectFreshTrendingSnapshot, StringComparison.Ordinal);
        Assert.Contains("ORDER BY generated_at_utc DESC", TimescaleMarketDataSql.SelectFreshTrendingSnapshot, StringComparison.Ordinal);
        Assert.Contains("ORDER BY snapshot.score DESC, snapshot.symbol ASC", TimescaleMarketDataSql.SelectFreshTrendingSnapshot, StringComparison.Ordinal);
    }

    [Fact]
    public void SqlDoesNotUseRegularWorkspacePostgresSchemaOrConnectionName()
    {
        var allSql = string.Concat(
            TimescaleMarketDataSql.Initialize,
            TimescaleMarketDataSql.UpsertCandle,
            TimescaleMarketDataSql.SelectFreshCandles,
            TimescaleMarketDataSql.UpsertTrendingSnapshotSymbol,
            TimescaleMarketDataSql.SelectFreshTrendingSnapshot);

        Assert.DoesNotContain("atrade_workspaces", allSql, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("workspace_watchlist", allSql, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("ConnectionStrings:postgres", allSql, StringComparison.OrdinalIgnoreCase);
    }
}
