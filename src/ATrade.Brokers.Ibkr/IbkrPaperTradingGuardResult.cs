namespace ATrade.Brokers.Ibkr;

public sealed record IbkrPaperTradingGuardResult(
    bool IsAllowed,
    string Code,
    string Message,
    string RequiredMode,
    string ConfiguredMode)
{
    public static IbkrPaperTradingGuardResult Allowed() => new(
        IsAllowed: true,
        Code: "paper-only",
        Message: "IBKR integration is restricted to Paper mode.",
        RequiredMode: nameof(IbkrAccountMode.Paper),
        ConfiguredMode: nameof(IbkrAccountMode.Paper));

    public static IbkrPaperTradingGuardResult Rejected(IbkrAccountMode configuredMode) => new(
        IsAllowed: false,
        Code: "live-trading-disabled",
        Message: $"IBKR integration rejects {configuredMode} mode. Only {IbkrAccountMode.Paper} is supported in this repository.",
        RequiredMode: nameof(IbkrAccountMode.Paper),
        ConfiguredMode: configuredMode.ToString());
}
