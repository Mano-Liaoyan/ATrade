namespace ATrade.MarketData;

public interface IMarketDataStreamingService
{
    bool TryCreateSnapshot(string symbol, string? chartRange, out MarketDataUpdate? update, out MarketDataError? error);

    Task<MarketDataReadResult<MarketDataUpdate>> CreateSnapshotAsync(
        string symbol,
        string? chartRange,
        CancellationToken cancellationToken = default);

    string GetGroupName(string symbol, string chartRange);
}

public sealed class MarketDataStreamingService(
    IMarketDataProvider marketDataProvider,
    IMarketDataStreamingProvider streamingProvider) : IMarketDataStreamingService
{
    public bool TryCreateSnapshot(string symbol, string? chartRange, out MarketDataUpdate? update, out MarketDataError? error) =>
        throw new NotSupportedException("Synchronous market-data streaming snapshots are no longer supported. Use CreateSnapshotAsync.");

    public async Task<MarketDataReadResult<MarketDataUpdate>> CreateSnapshotAsync(
        string symbol,
        string? chartRange,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (!ChartRangePresets.TryNormalize(chartRange, out var normalizedChartRange))
        {
            return MarketDataReadResult<MarketDataUpdate>.Failure(ChartRangePresets.CreateUnsupportedRangeError(chartRange));
        }

        var status = await marketDataProvider.GetStatusAsync(cancellationToken).ConfigureAwait(false);
        if (!status.IsAvailable)
        {
            return MarketDataReadResult<MarketDataUpdate>.Failure(status.ToError());
        }

        var result = await streamingProvider.CreateSnapshotAsync(symbol, normalizedChartRange, cancellationToken).ConfigureAwait(false);
        return result.IsSuccess && result.Value is not null
            ? result
            : MarketDataReadResult<MarketDataUpdate>.Failure(result.Error ?? new MarketDataError(
                MarketDataProviderErrorCodes.MarketDataRequestFailed,
                "Market-data snapshot request failed."));
    }

    public string GetGroupName(string symbol, string chartRange) =>
        streamingProvider.GetGroupName(symbol, ChartRangePresets.TryNormalize(chartRange, out var normalizedChartRange) ? normalizedChartRange : chartRange.Trim());
}
