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

        var resultEnvelope = CreateCompletedResultEnvelope(run.Run, candles, analysisResult);
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

    private static BacktestCompletedResultEnvelope CreateCompletedResultEnvelope(
        BacktestRunEnvelope run,
        CandleSeriesResponse candles,
        AnalysisResult analysis) =>
        new(
            SchemaVersion: "tp-061.backtest-result.v1",
            Status: BacktestRunStatuses.Completed,
            StrategyId: run.Request.StrategyId,
            Parameters: run.Request.Parameters.ToDictionary(
                parameter => parameter.Key,
                parameter => parameter.Value.Clone(),
                StringComparer.Ordinal),
            Engine: new BacktestResultEngineEnvelope(
                analysis.Engine.EngineId,
                analysis.Engine.DisplayName,
                analysis.Engine.Provider,
                analysis.Engine.Version,
                analysis.Engine.State,
                analysis.Engine.Message),
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
                    analysis.Backtest.WinRatePercent,
                    analysis.Backtest.MaxDrawdownPercent,
                    analysis.Backtest.TotalCost),
            EquityCurve: analysis.BacktestDetails?.EquityCurve.Select(point => new BacktestResultEquityCurvePointEnvelope(
                point.Time,
                point.Equity,
                point.DrawdownPercent)).ToArray() ?? [],
            Trades: analysis.BacktestDetails?.Trades.Select(trade => new BacktestResultTradeEnvelope(
                trade.EntryTime,
                trade.ExitTime,
                trade.Direction,
                trade.EntryPrice,
                trade.ExitPrice,
                trade.Quantity,
                trade.GrossPnl,
                trade.NetPnl,
                trade.ReturnPercent,
                trade.TotalCost,
                trade.ExitReason)).ToArray() ?? [],
            Benchmark: CreateBuyAndHoldBenchmark(run, candles),
            Accounting: new BacktestResultAccountingEnvelope(
                run.Request.CostModel.CommissionPerTrade,
                run.Request.CostModel.CommissionBps,
                run.Request.SlippageBps,
                run.Request.CostModel.Currency));

    private static BacktestResultBenchmarkEnvelope? CreateBuyAndHoldBenchmark(
        BacktestRunEnvelope run,
        CandleSeriesResponse candles)
    {
        if (!string.Equals(run.Request.BenchmarkMode, BacktestBenchmarkModes.BuyAndHold, StringComparison.OrdinalIgnoreCase) ||
            candles.Candles.Count == 0)
        {
            return null;
        }

        var firstClose = candles.Candles[0].Close;
        if (firstClose <= 0)
        {
            return null;
        }

        var equityCurve = candles.Candles
            .Select(candle => new BacktestResultEquityCurvePointEnvelope(
                candle.Time.ToUniversalTime(),
                decimal.Round(run.Capital.InitialCapital * (candle.Close / firstClose), 4, MidpointRounding.AwayFromZero),
                0m))
            .ToArray();

        var peak = 0m;
        for (var index = 0; index < equityCurve.Length; index++)
        {
            peak = Math.Max(peak, equityCurve[index].Equity);
            var drawdownPercent = peak <= 0m
                ? 0m
                : decimal.Round(Math.Max(0m, ((peak - equityCurve[index].Equity) / peak) * 100m), 4, MidpointRounding.AwayFromZero);
            equityCurve[index] = equityCurve[index] with { DrawdownPercent = drawdownPercent };
        }

        var finalEquity = equityCurve[^1].Equity;
        var totalReturnPercent = run.Capital.InitialCapital <= 0m
            ? 0m
            : decimal.Round(((finalEquity / run.Capital.InitialCapital) - 1m) * 100m, 4, MidpointRounding.AwayFromZero);

        return new BacktestResultBenchmarkEnvelope(
            BacktestBenchmarkModes.BuyAndHold,
            "Buy and hold",
            run.Capital.InitialCapital,
            finalEquity,
            totalReturnPercent,
            equityCurve);
    }
}
