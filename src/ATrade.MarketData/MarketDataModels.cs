namespace ATrade.MarketData;

public static class MarketDataTimeframes
{
    public const string OneMinute = ChartRangePresets.OneMinute;
    public const string FiveMinutes = ChartRangePresets.FiveMinutes;
    public const string OneHour = ChartRangePresets.OneHour;
    public const string SixHours = ChartRangePresets.SixHours;
    public const string OneDay = ChartRangePresets.OneDay;
    public const string OneMonth = ChartRangePresets.OneMonth;
    public const string SixMonths = ChartRangePresets.SixMonths;
    public const string OneYear = ChartRangePresets.OneYear;
    public const string FiveYears = ChartRangePresets.FiveYears;
    public const string All = ChartRangePresets.All;
    public const string Default = ChartRangePresets.Default;

    public static IReadOnlyList<string> Supported => ChartRangePresets.Supported;

    public static bool TryGetDefinition(string? timeframe, out TimeframeDefinition definition) =>
        TryGetDefinition(timeframe, DateTimeOffset.UtcNow, out definition);

    public static bool TryGetDefinition(string? timeframe, DateTimeOffset nowUtc, out TimeframeDefinition definition)
    {
        if (!ChartRangePresets.TryGetPreset(timeframe, out var preset))
        {
            definition = default;
            return false;
        }

        definition = TimeframeDefinition.FromPreset(preset, nowUtc);
        return true;
    }
}

public readonly record struct TimeframeDefinition(
    string Name,
    TimeSpan Step,
    int CandleCount,
    string ProviderPeriod,
    string ProviderBarSize,
    DateTimeOffset? LookbackStartUtc)
{
    public static TimeframeDefinition FromPreset(ChartRangePreset preset, DateTimeOffset nowUtc) => new(
        preset.Value,
        ParseProviderBarStep(preset.ProviderBarSize),
        EstimateCandleCount(preset),
        preset.ProviderPeriod,
        preset.ProviderBarSize,
        preset.GetLookbackStartUtc(nowUtc));

    private static TimeSpan ParseProviderBarStep(string providerBarSize) => providerBarSize.Trim().ToLowerInvariant() switch
    {
        "1min" => TimeSpan.FromMinutes(1),
        "5min" => TimeSpan.FromMinutes(5),
        "1h" => TimeSpan.FromHours(1),
        "1d" => TimeSpan.FromDays(1),
        "1w" => TimeSpan.FromDays(7),
        _ => TimeSpan.FromDays(1),
    };

    private static int EstimateCandleCount(ChartRangePreset preset) => preset.Value switch
    {
        ChartRangePresets.OneMinute => 1,
        ChartRangePresets.FiveMinutes => 5,
        ChartRangePresets.OneHour => 60,
        ChartRangePresets.SixHours => 72,
        ChartRangePresets.OneDay => 288,
        ChartRangePresets.OneMonth => 31,
        ChartRangePresets.SixMonths => 190,
        ChartRangePresets.OneYear => 370,
        ChartRangePresets.FiveYears => 260,
        ChartRangePresets.All => 520,
        _ => 180,
    };
}

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

    bool TryGetCandles(string symbol, string? chartRange, out CandleSeriesResponse? response, out MarketDataError? error, MarketDataSymbolIdentity? identity = null);

    bool TryGetIndicators(string symbol, string? chartRange, out IndicatorResponse? response, out MarketDataError? error, MarketDataSymbolIdentity? identity = null);

    bool TryGetLatestUpdate(string symbol, string? chartRange, out MarketDataUpdate? update, out MarketDataError? error, MarketDataSymbolIdentity? identity = null);

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
        string? chartRange,
        MarketDataSymbolIdentity? identity = null,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (!TryNormalizeChartRange(chartRange, out var normalizedChartRange, out var rangeError))
        {
            return Task.FromResult(MarketDataReadResult<CandleSeriesResponse>.Failure(rangeError!));
        }

        return Task.FromResult(
            TryGetCandles(symbol, normalizedChartRange, out var response, out var error, identity) && response is not null
                ? MarketDataReadResult<CandleSeriesResponse>.Success(response)
                : MarketDataReadResult<CandleSeriesResponse>.Failure(ToReadError(error)));
    }

    Task<MarketDataReadResult<IndicatorResponse>> GetIndicatorsAsync(
        string symbol,
        string? chartRange,
        MarketDataSymbolIdentity? identity = null,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (!TryNormalizeChartRange(chartRange, out var normalizedChartRange, out var rangeError))
        {
            return Task.FromResult(MarketDataReadResult<IndicatorResponse>.Failure(rangeError!));
        }

        return Task.FromResult(
            TryGetIndicators(symbol, normalizedChartRange, out var response, out var error, identity) && response is not null
                ? MarketDataReadResult<IndicatorResponse>.Success(response)
                : MarketDataReadResult<IndicatorResponse>.Failure(ToReadError(error)));
    }

    Task<MarketDataReadResult<MarketDataUpdate>> GetLatestUpdateAsync(
        string symbol,
        string? chartRange,
        MarketDataSymbolIdentity? identity = null,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (!TryNormalizeChartRange(chartRange, out var normalizedChartRange, out var rangeError))
        {
            return Task.FromResult(MarketDataReadResult<MarketDataUpdate>.Failure(rangeError!));
        }

        return Task.FromResult(
            TryGetLatestUpdate(symbol, normalizedChartRange, out var update, out var error, identity) && update is not null
                ? MarketDataReadResult<MarketDataUpdate>.Success(update)
                : MarketDataReadResult<MarketDataUpdate>.Failure(ToReadError(error)));
    }

    private static bool TryNormalizeChartRange(string? chartRange, out string normalizedChartRange, out MarketDataError? error)
    {
        if (ChartRangePresets.TryNormalize(chartRange, out normalizedChartRange))
        {
            error = null;
            return true;
        }

        error = ChartRangePresets.CreateUnsupportedRangeError(chartRange);
        return false;
    }

    private static MarketDataError ToReadError(MarketDataError? error) => error ?? new MarketDataError(
        MarketDataProviderErrorCodes.MarketDataRequestFailed,
        "Market-data request failed.");
}
