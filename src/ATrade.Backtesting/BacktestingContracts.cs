using System.Text.Json;
using System.Text.Json.Serialization;
using ATrade.Accounts;
using ATrade.MarketData;

namespace ATrade.Backtesting;

public static class BacktestRunStatuses
{
    public const string Queued = "queued";
    public const string Running = "running";
    public const string Completed = "completed";
    public const string Failed = "failed";
    public const string Cancelled = "cancelled";

    public static IReadOnlyList<string> Supported { get; } =
        [Queued, Running, Completed, Failed, Cancelled];

    public static bool IsSupported(string? status) =>
        !string.IsNullOrWhiteSpace(status) && Supported.Contains(status.Trim(), StringComparer.OrdinalIgnoreCase);

    public static bool CanCancel(string status) =>
        string.Equals(status, Queued, StringComparison.OrdinalIgnoreCase) ||
        string.Equals(status, Running, StringComparison.OrdinalIgnoreCase);

    public static bool CanRetry(string status) =>
        string.Equals(status, Failed, StringComparison.OrdinalIgnoreCase) ||
        string.Equals(status, Cancelled, StringComparison.OrdinalIgnoreCase);

    public static bool IsTerminal(string status) =>
        string.Equals(status, Completed, StringComparison.OrdinalIgnoreCase) ||
        string.Equals(status, Failed, StringComparison.OrdinalIgnoreCase) ||
        string.Equals(status, Cancelled, StringComparison.OrdinalIgnoreCase);
}

public static class BacktestStrategyIds
{
    public const string SmaCrossover = "sma-crossover";
    public const string RsiMeanReversion = "rsi-mean-reversion";
    public const string Breakout = "breakout";

    public static IReadOnlyList<string> BuiltIn { get; } =
        [SmaCrossover, RsiMeanReversion, Breakout];

    public static string SupportedValuesMessage => string.Join(", ", BuiltIn);

    public static bool TryNormalize(string? strategyId, out string normalizedStrategyId)
    {
        normalizedStrategyId = string.Empty;
        if (string.IsNullOrWhiteSpace(strategyId))
        {
            return false;
        }

        var candidate = strategyId.Trim().ToLowerInvariant();
        if (!BuiltIn.Contains(candidate, StringComparer.Ordinal))
        {
            return false;
        }

        normalizedStrategyId = candidate;
        return true;
    }
}

public static class BacktestBenchmarkModes
{
    public const string None = "none";
    public const string BuyAndHold = "buy-and-hold";
    public const string Default = None;

    public static IReadOnlyList<string> Supported { get; } = [None, BuyAndHold];

    public static string SupportedValuesMessage => string.Join(", ", Supported);

    public static bool TryNormalize(string? benchmarkMode, out string normalizedBenchmarkMode)
    {
        normalizedBenchmarkMode = string.IsNullOrWhiteSpace(benchmarkMode)
            ? Default
            : benchmarkMode.Trim().ToLowerInvariant();

        return Supported.Contains(normalizedBenchmarkMode, StringComparer.Ordinal);
    }
}

public static class BacktestDefaults
{
    public const string Currency = LocalPaperCapitalValidator.DefaultCurrency;
    public const decimal DefaultCommissionPerTrade = 0m;
    public const decimal DefaultCommissionBps = 0m;
    public const decimal DefaultSlippageBps = 0m;
}

public static class BacktestValidationLimits
{
    public const int MaximumParameterCount = 32;
    public const int MaximumParameterNameLength = 64;
    public const int MaximumParameterStringLength = 256;
    public const int MaximumParameterDepth = 4;
    public const decimal MaximumCommissionPerTrade = 1_000m;
    public const decimal MaximumCommissionBps = 1_000m;
    public const decimal MaximumSlippageBps = 1_000m;
}

public static class BacktestErrorCodes
{
    public const string InvalidPayload = "backtest-invalid-payload";
    public const string InvalidSymbol = "backtest-invalid-symbol";
    public const string UnsupportedChartRange = "backtest-unsupported-chart-range";
    public const string UnsupportedStrategy = "backtest-unsupported-strategy";
    public const string InvalidParameters = "backtest-invalid-parameters";
    public const string InvalidCostModel = "backtest-invalid-cost-model";
    public const string InvalidSlippage = "backtest-invalid-slippage";
    public const string InvalidBenchmark = "backtest-invalid-benchmark";
    public const string UnsupportedScope = "backtest-unsupported-scope";
    public const string ForbiddenField = "backtest-forbidden-field";
    public const string CapitalUnavailable = "backtest-capital-unavailable";
    public const string StorageUnavailable = "backtest-storage-unavailable";
    public const string RunNotFound = "backtest-run-not-found";
    public const string InvalidStatusTransition = "backtest-invalid-status-transition";
}

public static class BacktestSafeMessages
{
    public const string InvalidPayload = "A backtest request payload is required.";
    public const string InvalidSymbol = "A single stock symbol or exact symbol identity is required.";
    public const string UnsupportedStrategy = "Backtests may use only built-in strategy IDs.";
    public const string UnsupportedScope = "Backtests currently support exactly one stock symbol per run.";
    public const string DirectBarsNotAllowed = "Backtests load market-data bars on the server; browser-submitted candles are not accepted.";
    public const string CustomCodeNotAllowed = "Custom strategy code is not accepted for saved backtests.";
    public const string OrderRoutingNotAllowed = "Backtest requests must not include order-routing or broker-execution fields.";
    public const string CapitalUnavailable = "No effective paper capital source is configured for backtest creation.";
    public const string StorageUnavailable = "Backtest storage is unavailable.";
    public const string RunNotFound = "Backtest run was not found.";
}

public sealed record BacktestRunId(string Value)
{
    public static BacktestRunId New() => new($"bt_{Guid.NewGuid():N}");

    public static BacktestRunId Create(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            throw new ArgumentException("A backtest run id is required.", nameof(value));
        }

        return new BacktestRunId(value.Trim());
    }

    public override string ToString() => Value;
}

public sealed record BacktestWorkspaceScope(string UserId, string WorkspaceId)
{
    public static BacktestWorkspaceScope From(PaperCapitalIdentity identity)
    {
        ArgumentNullException.ThrowIfNull(identity);
        return new BacktestWorkspaceScope(identity.UserId, identity.WorkspaceId);
    }
}

public sealed record BacktestCostModel(decimal? CommissionPerTrade, decimal? CommissionBps, string? Currency)
{
    [JsonExtensionData]
    public IDictionary<string, JsonElement>? AdditionalProperties { get; init; }
}

public sealed record BacktestCostModelSnapshot(decimal CommissionPerTrade, decimal CommissionBps, string Currency);

public sealed record BacktestCreateRequest(
    MarketDataSymbolIdentity? Symbol,
    string? SymbolCode,
    string? StrategyId,
    IDictionary<string, JsonElement>? Parameters,
    string? ChartRange,
    BacktestCostModel? CostModel,
    decimal? SlippageBps,
    string? BenchmarkMode)
{
    [JsonExtensionData]
    public IDictionary<string, JsonElement>? AdditionalProperties { get; init; }
}

public sealed record BacktestRequestSnapshot(
    MarketDataSymbolIdentity Symbol,
    string StrategyId,
    IReadOnlyDictionary<string, JsonElement> Parameters,
    string ChartRange,
    BacktestCostModelSnapshot CostModel,
    decimal SlippageBps,
    string BenchmarkMode);

public sealed record BacktestCapitalSnapshot(decimal InitialCapital, string Currency, string CapitalSource);

public sealed record BacktestError(string Code, string Message);

public sealed record BacktestRunEnvelope(
    string Id,
    string Status,
    BacktestRequestSnapshot Request,
    BacktestCapitalSnapshot Capital,
    DateTimeOffset CreatedAtUtc,
    DateTimeOffset UpdatedAtUtc,
    DateTimeOffset? StartedAtUtc,
    DateTimeOffset? CompletedAtUtc,
    BacktestError? Error,
    JsonElement? Result);

public sealed record BacktestRunRecord(BacktestWorkspaceScope Scope, BacktestRunEnvelope Run);

public sealed record BacktestCreateResult(BacktestRunRecord? Run, BacktestError? Error)
{
    public bool IsSuccess => Run is not null;

    public static BacktestCreateResult Success(BacktestRunRecord run)
    {
        ArgumentNullException.ThrowIfNull(run);
        return new BacktestCreateResult(run, null);
    }

    public static BacktestCreateResult Failure(string code, string message) =>
        new(null, new BacktestError(code, message));
}
