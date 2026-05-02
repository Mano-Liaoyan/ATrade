using ATrade.MarketData;

namespace ATrade.MarketData.Timescale;

public sealed record TimescaleMarketDataSymbol(
    string Provider,
    string? ProviderSymbolId,
    string Symbol,
    string? Name,
    string? Exchange,
    string? Currency,
    string? AssetClass)
{
    public static TimescaleMarketDataSymbol FromIdentity(MarketDataSymbolIdentity identity, string? name = null)
    {
        ArgumentNullException.ThrowIfNull(identity);

        var exactIdentity = identity.ToExactInstrumentIdentity();
        return new TimescaleMarketDataSymbol(
            exactIdentity.Provider,
            exactIdentity.ProviderSymbolId,
            exactIdentity.Symbol,
            name,
            exactIdentity.Exchange,
            exactIdentity.Currency,
            exactIdentity.AssetClass);
    }

    public MarketDataSymbolIdentity ToMarketDataSymbolIdentity() => MarketDataSymbolIdentity.Create(
        Symbol,
        Provider,
        ProviderSymbolId,
        AssetClass,
        Exchange,
        Currency);
}

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
    DateTimeOffset FreshnessCutoffUtc,
    string? ProviderSymbolId = null,
    string? Exchange = null,
    string? Currency = null,
    string? AssetClass = null);

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
    string? Symbol = null,
    string? ProviderSymbolId = null,
    string? Exchange = null,
    string? Currency = null,
    string? AssetClass = null);
