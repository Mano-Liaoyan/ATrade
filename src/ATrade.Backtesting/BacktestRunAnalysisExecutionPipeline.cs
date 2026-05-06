using System.Text.Json;
using ATrade.Analysis;
using ATrade.MarketData;

namespace ATrade.Backtesting;

public sealed class BacktestRunAnalysisExecutionPipeline(
    IMarketDataService marketDataService,
    IAnalysisEngineRegistry analysisEngines,
    TimeProvider timeProvider) : IBacktestRunExecutionPipeline
{
    private static readonly JsonSerializerOptions ResultSerializerOptions = new(JsonSerializerDefaults.Web);

    public BacktestRunAnalysisExecutionPipeline(
        IMarketDataService marketDataService,
        IAnalysisEngineRegistry analysisEngines)
        : this(marketDataService, analysisEngines, TimeProvider.System)
    {
    }

    public async Task<BacktestRunExecutionResult> ExecuteAsync(
        BacktestRunRecord run,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(run);
        cancellationToken.ThrowIfCancellationRequested();

        var request = run.Run.Request;
        var candleRead = await marketDataService
            .GetCandlesAsync(request.Symbol.Symbol, request.ChartRange, request.Symbol, cancellationToken)
            .ConfigureAwait(false);
        if (candleRead.IsFailure || candleRead.Value is null)
        {
            var error = ToBacktestMarketDataError(candleRead.Error);
            return BacktestRunExecutionResult.Failed(error.Code, error.Message);
        }

        var candles = candleRead.Value;
        if (candles.Candles.Count == 0)
        {
            return BacktestRunExecutionResult.Failed(
                BacktestErrorCodes.MarketDataUnavailable,
                BacktestSafeMessages.MarketDataUnavailable);
        }

        var analysisRequest = new AnalysisRequest(
            candles.Identity ?? request.Symbol,
            candles.Timeframe,
            timeProvider.GetUtcNow(),
            candles.Candles,
            EngineId: request.EngineId,
            StrategyName: request.StrategyId,
            StrategyParameters: request.Parameters,
            BacktestSettings: new AnalysisBacktestSettings(
                run.Run.Capital.InitialCapital,
                request.CostModel.CommissionPerTrade,
                request.CostModel.CommissionBps,
                request.SlippageBps,
                request.CostModel.Currency));

        var analysisResult = await analysisEngines.AnalyzeAsync(analysisRequest, cancellationToken).ConfigureAwait(false);
        if (!string.Equals(analysisResult.Status, AnalysisResultStatuses.Completed, StringComparison.OrdinalIgnoreCase))
        {
            var error = ToBacktestAnalysisError(analysisResult);
            return BacktestRunExecutionResult.Failed(error.Code, error.Message);
        }

        var resultEnvelope = BacktestCompletedResultEnvelope.From(run.Run, candles, analysisResult);
        return BacktestRunExecutionResult.Completed(JsonSerializer.SerializeToElement(resultEnvelope, ResultSerializerOptions));
    }

    private static BacktestError ToBacktestMarketDataError(MarketDataError? error)
    {
        if (error is null)
        {
            return new BacktestError(
                BacktestErrorCodes.MarketDataUnavailable,
                BacktestSafeMessages.MarketDataUnavailable);
        }

        var (code, message) = error.Code switch
        {
            MarketDataProviderErrorCodes.ProviderNotConfigured => (error.Code, "Market-data provider is not configured for backtest execution."),
            MarketDataProviderErrorCodes.ProviderUnavailable => (error.Code, "Market-data provider is unavailable for backtest execution."),
            MarketDataProviderErrorCodes.AuthenticationRequired => (error.Code, "Market-data provider authentication is required for backtest execution."),
            MarketDataProviderErrorCodes.UnsupportedSymbol => (error.Code, "Market-data provider does not support the saved backtest symbol."),
            MarketDataProviderErrorCodes.UnsupportedChartRange => (error.Code, "Saved backtest chart range is not supported by the market-data provider."),
            _ => (BacktestErrorCodes.MarketDataUnavailable, BacktestSafeMessages.MarketDataUnavailable),
        };

        return BacktestPersistenceSafety.NormalizeSafeError(new BacktestError(code, message)) ?? new BacktestError(
            BacktestErrorCodes.MarketDataUnavailable,
            BacktestSafeMessages.MarketDataUnavailable);
    }

    private static BacktestError ToBacktestAnalysisError(AnalysisResult result)
    {
        var (errorCode, message) = result.Error?.Code switch
        {
            AnalysisEngineErrorCodes.EngineNotConfigured => (AnalysisEngineErrorCodes.EngineNotConfigured, "No analysis engine is configured for backtest execution."),
            AnalysisEngineErrorCodes.EngineUnavailable => (AnalysisEngineErrorCodes.EngineUnavailable, "Analysis engine is unavailable for backtest execution."),
            AnalysisEngineErrorCodes.InvalidRequest => (AnalysisEngineErrorCodes.InvalidRequest, "Analysis engine rejected the saved backtest request."),
            _ => (BacktestErrorCodes.AnalysisUnavailable, BacktestSafeMessages.AnalysisUnavailable),
        };

        return BacktestPersistenceSafety.NormalizeSafeError(new BacktestError(errorCode, message)) ?? new BacktestError(
            BacktestErrorCodes.AnalysisUnavailable,
            BacktestSafeMessages.AnalysisUnavailable);
    }

    private sealed record BacktestCompletedResultEnvelope(
        string SchemaVersion,
        string Status,
        string StrategyId,
        BacktestResultEngineEnvelope Engine,
        BacktestResultSymbolEnvelope Symbol,
        string ChartRange,
        DateTimeOffset GeneratedAtUtc,
        BacktestResultSourceEnvelope Source,
        IReadOnlyList<BacktestResultSignalEnvelope> Signals,
        IReadOnlyList<BacktestResultMetricEnvelope> Metrics,
        BacktestResultSummaryEnvelope? Backtest)
    {
        public static BacktestCompletedResultEnvelope From(
            BacktestRunEnvelope run,
            CandleSeriesResponse candles,
            AnalysisResult analysis) =>
            new(
                SchemaVersion: "tp-060.backtest-result.v1",
                Status: BacktestRunStatuses.Completed,
                StrategyId: run.Request.StrategyId,
                Engine: new BacktestResultEngineEnvelope(
                    analysis.Engine.EngineId,
                    analysis.Engine.DisplayName,
                    analysis.Engine.Provider,
                    analysis.Engine.Version,
                    analysis.Engine.State),
                Symbol: new BacktestResultSymbolEnvelope(
                    analysis.Symbol.Symbol,
                    analysis.Symbol.Provider,
                    analysis.Symbol.ProviderSymbolId,
                    analysis.Symbol.AssetClass,
                    analysis.Symbol.Exchange,
                    analysis.Symbol.Currency),
                ChartRange: candles.Timeframe,
                GeneratedAtUtc: analysis.GeneratedAtUtc,
                Source: new BacktestResultSourceEnvelope(
                    analysis.Source.Provider,
                    candles.Source,
                    analysis.Source.GeneratedAtUtc),
                Signals: analysis.Signals.Select(signal => new BacktestResultSignalEnvelope(
                    signal.Time,
                    signal.Kind,
                    signal.Direction,
                    signal.Confidence,
                    signal.Rationale)).ToArray(),
                Metrics: analysis.Metrics.Select(metric => new BacktestResultMetricEnvelope(
                    metric.Name,
                    metric.Value,
                    metric.Unit)).ToArray(),
                Backtest: analysis.Backtest is null
                    ? null
                    : new BacktestResultSummaryEnvelope(
                        analysis.Backtest.StartUtc,
                        analysis.Backtest.EndUtc,
                        analysis.Backtest.InitialCapital,
                        analysis.Backtest.FinalEquity,
                        analysis.Backtest.TotalReturnPercent,
                        analysis.Backtest.TradeCount,
                        analysis.Backtest.WinRatePercent));
    }

    private sealed record BacktestResultEngineEnvelope(
        string EngineId,
        string DisplayName,
        string Provider,
        string Version,
        string State);

    private sealed record BacktestResultSymbolEnvelope(
        string Symbol,
        string Provider,
        string? ProviderSymbolId,
        string AssetClass,
        string Exchange,
        string Currency);

    private sealed record BacktestResultSourceEnvelope(
        string Provider,
        string MarketDataSource,
        DateTimeOffset GeneratedAtUtc);

    private sealed record BacktestResultSignalEnvelope(
        DateTimeOffset Time,
        string Kind,
        string Direction,
        decimal Confidence,
        string Rationale);

    private sealed record BacktestResultMetricEnvelope(string Name, decimal Value, string? Unit);

    private sealed record BacktestResultSummaryEnvelope(
        DateTimeOffset StartUtc,
        DateTimeOffset EndUtc,
        decimal InitialCapital,
        decimal FinalEquity,
        decimal TotalReturnPercent,
        int TradeCount,
        decimal WinRatePercent);
}
