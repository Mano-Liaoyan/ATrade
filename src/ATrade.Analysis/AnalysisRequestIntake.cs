using ATrade.MarketData;

namespace ATrade.Analysis;

public interface IAnalysisRequestIntake
{
    ValueTask<AnalysisRunIntakeResult> RunAsync(AnalysisRunRequest? request, CancellationToken cancellationToken = default);
}

public sealed record AnalysisRunRequest(
    MarketDataSymbolIdentity? Symbol,
    string? SymbolCode,
    string? Timeframe,
    DateTimeOffset? RequestedAtUtc,
    IReadOnlyList<OhlcvCandle>? Bars,
    string? EngineId,
    string? StrategyName);

public sealed record AnalysisRunIntakeResult(
    AnalysisResult? Result,
    AnalysisError? InvalidRequestError,
    MarketDataError? MarketDataError)
{
    public bool IsSuccess => Result is not null;

    public static AnalysisRunIntakeResult Success(AnalysisResult result)
    {
        ArgumentNullException.ThrowIfNull(result);
        return new AnalysisRunIntakeResult(result, null, null);
    }

    public static AnalysisRunIntakeResult InvalidRequest(string message) => new(
        null,
        new AnalysisError(AnalysisEngineErrorCodes.InvalidRequest, message),
        null);

    public static AnalysisRunIntakeResult MarketDataFailure(MarketDataError error)
    {
        ArgumentNullException.ThrowIfNull(error);
        return new AnalysisRunIntakeResult(null, null, error);
    }
}

public sealed class AnalysisRequestIntake(
    IMarketDataService marketDataService,
    IAnalysisEngineRegistry analysisEngines) : IAnalysisRequestIntake
{
    public async ValueTask<AnalysisRunIntakeResult> RunAsync(AnalysisRunRequest? request, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (request is null)
        {
            return AnalysisRunIntakeResult.InvalidRequest("An analysis request payload is required.");
        }

        var timeframe = string.IsNullOrWhiteSpace(request.Timeframe) ? MarketDataTimeframes.OneDay : request.Timeframe.Trim();
        var requestedIdentity = request.Symbol;
        var symbol = requestedIdentity ?? CreateSymbolIdentityFromCode(request.SymbolCode);
        var bars = request.Bars;

        if (bars is null || bars.Count == 0)
        {
            var symbolCode = requestedIdentity?.Symbol ?? request.SymbolCode;
            if (string.IsNullOrWhiteSpace(symbolCode))
            {
                return AnalysisRunIntakeResult.InvalidRequest("A symbol or symbolCode is required for analysis.");
            }

            var candleRead = await marketDataService
                .GetCandlesAsync(symbolCode, timeframe, requestedIdentity, cancellationToken)
                .ConfigureAwait(false);
            if (candleRead.IsFailure || candleRead.Value is null)
            {
                return AnalysisRunIntakeResult.MarketDataFailure(ToMarketDataError(candleRead.Error));
            }

            var candleSeries = candleRead.Value;
            if (candleSeries.Candles.Count == 0)
            {
                return AnalysisRunIntakeResult.InvalidRequest("Market-data provider returned no candles for analysis.");
            }

            bars = candleSeries.Candles;
            timeframe = candleSeries.Timeframe;
            symbol = await ResolveSymbolIdentityAsync(requestedIdentity, candleSeries, cancellationToken).ConfigureAwait(false);
        }

        if (symbol is null)
        {
            return AnalysisRunIntakeResult.InvalidRequest("A symbol identity is required when analysis bars are supplied directly.");
        }

        cancellationToken.ThrowIfCancellationRequested();
        var analysisRequest = new AnalysisRequest(
            symbol,
            timeframe,
            request.RequestedAtUtc ?? DateTimeOffset.UtcNow,
            bars,
            request.EngineId,
            request.StrategyName);

        return AnalysisRunIntakeResult.Success(await analysisEngines.AnalyzeAsync(analysisRequest, cancellationToken).ConfigureAwait(false));
    }

    private static MarketDataSymbolIdentity? CreateSymbolIdentityFromCode(string? symbolCode)
    {
        return string.IsNullOrWhiteSpace(symbolCode)
            ? null
            : MarketDataSymbolIdentity.Create(symbolCode, "market-data-provider", null, MarketDataAssetClasses.Stock, "UNKNOWN", "USD");
    }

    private async Task<MarketDataSymbolIdentity> ResolveSymbolIdentityAsync(
        MarketDataSymbolIdentity? requestedIdentity,
        CandleSeriesResponse candleSeries,
        CancellationToken cancellationToken)
    {
        if (candleSeries.Identity is not null)
        {
            return candleSeries.Identity;
        }

        if (requestedIdentity is not null)
        {
            return requestedIdentity;
        }

        var symbolRead = await marketDataService.GetSymbolAsync(candleSeries.Symbol, cancellationToken).ConfigureAwait(false);
        if (symbolRead.IsSuccess && symbolRead.Value is not null)
        {
            var marketSymbol = symbolRead.Value;
            return marketSymbol.Identity ?? MarketDataSymbolIdentity.Create(
                marketSymbol.Symbol,
                candleSeries.Source,
                providerSymbolId: null,
                marketSymbol.AssetClass,
                marketSymbol.Exchange,
                currency: "USD");
        }

        return MarketDataSymbolIdentity.Create(
            candleSeries.Symbol,
            candleSeries.Source,
            providerSymbolId: null,
            MarketDataAssetClasses.Stock,
            exchange: "UNKNOWN",
            currency: "USD");
    }

    private static MarketDataError ToMarketDataError(MarketDataError? error) => error ?? new MarketDataError(
        MarketDataProviderErrorCodes.MarketDataRequestFailed,
        "Market-data request failed.");
}
