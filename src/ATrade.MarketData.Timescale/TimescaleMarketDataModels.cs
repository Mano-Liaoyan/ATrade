using ATrade.MarketData;

namespace ATrade.MarketData.Timescale;

public sealed record TimescaleMarketDataSymbol(
    string Provider,
    string? ProviderSymbolId,
    string Symbol,
    string? Name,
    string? Exchange,
    string? Currency,
    string? AssetClass);

public sealed record TimescaleCandleSeries(
    TimescaleMarketDataSymbol Symbol,
    string Timeframe,
    string Source,
    DateTimeOffset GeneratedAtUtc,
    IReadOnlyList<OhlcvCandle> Candles);

public sealed record TimescaleFreshCandleSeriesQuery(
    string Provider,
    string? Source,
    string Symbol,
    string Timeframe,
    DateTimeOffset FreshnessCutoffUtc);

public sealed record TimescaleTrendingSnapshot(
    string Provider,
    string Source,
    DateTimeOffset GeneratedAtUtc,
    IReadOnlyList<TimescaleTrendingSnapshotSymbol> Symbols);

public sealed record TimescaleTrendingSnapshotSymbol(
    TimescaleMarketDataSymbol Symbol,
    string? Sector,
    decimal LastPrice,
    decimal ChangePercent,
    decimal Score,
    TrendingFactorBreakdown Factors,
    IReadOnlyList<string> Reasons);

public sealed record TimescaleFreshTrendingSnapshotQuery(
    string Provider,
    string? Source,
    DateTimeOffset FreshnessCutoffUtc,
    string? Symbol = null);
