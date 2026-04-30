namespace ATrade.Analysis.Lean;

public static class LeanAnalysisGuardrails
{
    private static readonly string[] ForbiddenRuntimeTokens =
    {
        "MarketOrder(",
        "LimitOrder(",
        "StopMarketOrder(",
        "StopLimitOrder(",
        "Liquidate(",
        "SetBrokerageModel",
        "BrokerageName.",
        "SetLiveMode",
        "IBrokerage",
        "/api/orders",
    };

    public static void EnsureAnalysisOnly(string algorithmSource)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(algorithmSource);

        foreach (var token in ForbiddenRuntimeTokens)
        {
            if (algorithmSource.Contains(token, StringComparison.OrdinalIgnoreCase))
            {
                throw new LeanAnalysisOnlyViolationException($"LEAN analysis source contains forbidden trading token '{token}'.");
            }
        }
    }
}

public sealed class LeanAnalysisOnlyViolationException(string message) : Exception(message);
