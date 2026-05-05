using System.Text.Json;

namespace ATrade.Backtesting;

public static class BacktestRequestSnapshots
{
    public static BacktestCreateRequest ToCreateRequest(BacktestRequestSnapshot requestSnapshot)
    {
        var normalized = BacktestPersistenceSafety.NormalizeSafeRequestSnapshot(requestSnapshot);
        return new BacktestCreateRequest(
            Symbol: normalized.Symbol,
            SymbolCode: normalized.Symbol.Symbol,
            StrategyId: normalized.StrategyId,
            Parameters: normalized.Parameters.ToDictionary(
                parameter => parameter.Key,
                parameter => parameter.Value.Clone(),
                StringComparer.Ordinal),
            ChartRange: normalized.ChartRange,
            CostModel: new BacktestCostModel(
                normalized.CostModel.CommissionPerTrade,
                normalized.CostModel.CommissionBps,
                normalized.CostModel.Currency),
            SlippageBps: normalized.SlippageBps,
            BenchmarkMode: normalized.BenchmarkMode);
    }
}
