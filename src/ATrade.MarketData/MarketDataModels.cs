namespace ATrade.MarketData;

public static class MarketDataTimeframes
{
    public const string OneMinute = "1m";
    public const string FiveMinutes = "5m";
    public const string OneHour = "1h";
    public const string OneDay = "1D";

    private static readonly IReadOnlyDictionary<string, TimeframeDefinition> Definitions = new Dictionary<string, TimeframeDefinition>(StringComparer.OrdinalIgnoreCase)
    {
        [OneMinute] = new(OneMinute, TimeSpan.FromMinutes(1), 120),
        [FiveMinutes] = new(FiveMinutes, TimeSpan.FromMinutes(5), 120),
        [OneHour] = new(OneHour, TimeSpan.FromHours(1), 168),
        [OneDay] = new(OneDay, TimeSpan.FromDays(1), 180),
    };

    public static IReadOnlyList<string> Supported { get; } = new[]
    {
        OneMinute,
        FiveMinutes,
        OneHour,
        OneDay,
    };

    public static bool TryGetDefinition(string? timeframe, out TimeframeDefinition definition)
    {
        var normalized = string.IsNullOrWhiteSpace(timeframe) ? OneDay : timeframe.Trim();
        return Definitions.TryGetValue(normalized, out definition);
    }
}

public readonly record struct TimeframeDefinition(string Name, TimeSpan Step, int CandleCount);

public sealed record MarketDataSymbol(
    string Symbol,
    string Name,
    string AssetClass,
    string Exchange,
    string Sector,
    decimal LastPrice,
    decimal ChangePercent,
    long AverageVolume);

public sealed record TrendingFactorBreakdown(
    decimal VolumeSpike,
    decimal PriceMomentum,
    decimal Volatility,
    decimal ExternalSignal);

public sealed record TrendingSymbol(
    string Symbol,
    string Name,
    string AssetClass,
    string Exchange,
    string Sector,
    decimal LastPrice,
    decimal ChangePercent,
    decimal Score,
    TrendingFactorBreakdown Factors,
    IReadOnlyList<string> Reasons);

public sealed record TrendingSymbolsResponse(
    DateTimeOffset GeneratedAt,
    IReadOnlyList<TrendingSymbol> Symbols,
    string Source = "provider");

public sealed record OhlcvCandle(
    DateTimeOffset Time,
    decimal Open,
    decimal High,
    decimal Low,
    decimal Close,
    long Volume);

public sealed record CandleSeriesResponse(
    string Symbol,
    string Timeframe,
    DateTimeOffset GeneratedAt,
    IReadOnlyList<OhlcvCandle> Candles,
    string Source = "provider");

public sealed record MovingAveragePoint(DateTimeOffset Time, decimal Sma20, decimal Sma50);

public sealed record RsiPoint(DateTimeOffset Time, decimal Value);

public sealed record MacdPoint(DateTimeOffset Time, decimal Macd, decimal Signal, decimal Histogram);

public sealed record IndicatorResponse(
    string Symbol,
    string Timeframe,
    IReadOnlyList<MovingAveragePoint> MovingAverages,
    IReadOnlyList<RsiPoint> Rsi,
    IReadOnlyList<MacdPoint> Macd,
    string Source = "provider");

public sealed record MarketDataUpdate(
    string Symbol,
    string Timeframe,
    DateTimeOffset Time,
    decimal Open,
    decimal High,
    decimal Low,
    decimal Close,
    long Volume,
    decimal ChangePercent,
    string Source);

public sealed record MarketDataError(string Code, string Message);

public interface IMarketDataService
{
    TrendingSymbolsResponse GetTrendingSymbols();

    bool TryGetSymbol(string symbol, out MarketDataSymbol? marketSymbol);

    bool TryGetCandles(string symbol, string? timeframe, out CandleSeriesResponse? response, out MarketDataError? error);

    bool TryGetIndicators(string symbol, string? timeframe, out IndicatorResponse? response, out MarketDataError? error);

    bool TryGetLatestUpdate(string symbol, string? timeframe, out MarketDataUpdate? update, out MarketDataError? error);
}
