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
    long AverageVolume,
    MarketDataSymbolIdentity? Identity = null);

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
    IReadOnlyList<string> Reasons,
    MarketDataSymbolIdentity? Identity = null);

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
    string Source = "provider",
    MarketDataSymbolIdentity? Identity = null);

public sealed record MovingAveragePoint(DateTimeOffset Time, decimal Sma20, decimal Sma50);

public sealed record RsiPoint(DateTimeOffset Time, decimal Value);

public sealed record MacdPoint(DateTimeOffset Time, decimal Macd, decimal Signal, decimal Histogram);

public sealed record IndicatorResponse(
    string Symbol,
    string Timeframe,
    IReadOnlyList<MovingAveragePoint> MovingAverages,
    IReadOnlyList<RsiPoint> Rsi,
    IReadOnlyList<MacdPoint> Macd,
    string Source = "provider",
    MarketDataSymbolIdentity? Identity = null);

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
    string Source,
    MarketDataSymbolIdentity? Identity = null);

public sealed record MarketDataError(string Code, string Message);

public sealed record MarketDataReadResult<T> where T : class
{
    private MarketDataReadResult(T? value, MarketDataError? error)
    {
        Value = value;
        Error = error;
    }

    public bool IsSuccess => Error is null;

    public bool IsFailure => Error is not null;

    public T? Value { get; }

    public MarketDataError? Error { get; }

    public static MarketDataReadResult<T> Success(T value)
    {
        ArgumentNullException.ThrowIfNull(value);
        return new MarketDataReadResult<T>(value, null);
    }

    public static MarketDataReadResult<T> Failure(MarketDataError error)
    {
        ArgumentNullException.ThrowIfNull(error);
        return new MarketDataReadResult<T>(null, error);
    }
}

public interface IMarketDataService
{
    TrendingSymbolsResponse GetTrendingSymbols();

    bool TrySearchSymbols(string? query, string? assetClass, int? limit, out MarketDataSymbolSearchResponse? response, out MarketDataError? error);

    bool TryGetSymbol(string symbol, out MarketDataSymbol? marketSymbol);

    bool TryGetCandles(string symbol, string? timeframe, out CandleSeriesResponse? response, out MarketDataError? error, MarketDataSymbolIdentity? identity = null);

    bool TryGetIndicators(string symbol, string? timeframe, out IndicatorResponse? response, out MarketDataError? error, MarketDataSymbolIdentity? identity = null);

    bool TryGetLatestUpdate(string symbol, string? timeframe, out MarketDataUpdate? update, out MarketDataError? error, MarketDataSymbolIdentity? identity = null);

    Task<MarketDataReadResult<TrendingSymbolsResponse>> GetTrendingSymbolsAsync(CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        try
        {
            return Task.FromResult(MarketDataReadResult<TrendingSymbolsResponse>.Success(GetTrendingSymbols()));
        }
        catch (MarketDataProviderUnavailableException exception)
        {
            return Task.FromResult(MarketDataReadResult<TrendingSymbolsResponse>.Failure(exception.Error));
        }
    }

    Task<MarketDataReadResult<MarketDataSymbolSearchResponse>> SearchSymbolsAsync(
        string? query,
        string? assetClass,
        int? limit,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return Task.FromResult(
            TrySearchSymbols(query, assetClass, limit, out var response, out var error) && response is not null
                ? MarketDataReadResult<MarketDataSymbolSearchResponse>.Success(response)
                : MarketDataReadResult<MarketDataSymbolSearchResponse>.Failure(ToReadError(error)));
    }

    Task<MarketDataReadResult<MarketDataSymbol>> GetSymbolAsync(string symbol, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return Task.FromResult(
            TryGetSymbol(symbol, out var marketSymbol) && marketSymbol is not null
                ? MarketDataReadResult<MarketDataSymbol>.Success(marketSymbol)
                : MarketDataReadResult<MarketDataSymbol>.Failure(new MarketDataError(
                    MarketDataProviderErrorCodes.UnsupportedSymbol,
                    $"Market-data provider returned no symbol metadata for '{symbol}'.")));
    }

    Task<MarketDataReadResult<CandleSeriesResponse>> GetCandlesAsync(
        string symbol,
        string? timeframe,
        MarketDataSymbolIdentity? identity = null,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return Task.FromResult(
            TryGetCandles(symbol, timeframe, out var response, out var error, identity) && response is not null
                ? MarketDataReadResult<CandleSeriesResponse>.Success(response)
                : MarketDataReadResult<CandleSeriesResponse>.Failure(ToReadError(error)));
    }

    Task<MarketDataReadResult<IndicatorResponse>> GetIndicatorsAsync(
        string symbol,
        string? timeframe,
        MarketDataSymbolIdentity? identity = null,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return Task.FromResult(
            TryGetIndicators(symbol, timeframe, out var response, out var error, identity) && response is not null
                ? MarketDataReadResult<IndicatorResponse>.Success(response)
                : MarketDataReadResult<IndicatorResponse>.Failure(ToReadError(error)));
    }

    Task<MarketDataReadResult<MarketDataUpdate>> GetLatestUpdateAsync(
        string symbol,
        string? timeframe,
        MarketDataSymbolIdentity? identity = null,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return Task.FromResult(
            TryGetLatestUpdate(symbol, timeframe, out var update, out var error, identity) && update is not null
                ? MarketDataReadResult<MarketDataUpdate>.Success(update)
                : MarketDataReadResult<MarketDataUpdate>.Failure(ToReadError(error)));
    }

    private static MarketDataError ToReadError(MarketDataError? error) => error ?? new MarketDataError(
        MarketDataProviderErrorCodes.MarketDataRequestFailed,
        "Market-data request failed.");
}
