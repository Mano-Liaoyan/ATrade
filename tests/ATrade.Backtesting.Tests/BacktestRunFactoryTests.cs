using ATrade.Accounts;
using ATrade.Backtesting;
using ATrade.MarketData;

namespace ATrade.Backtesting.Tests;

public sealed class BacktestRunFactoryTests
{
    private static readonly PaperCapitalIdentity Identity = PaperCapitalIdentityDefaults.LocalPaperTradingWorkspace;

    [Fact]
    public async Task CreateQueuedRunAsync_SnapshotsEffectiveCapitalSourceCurrencyAndLocalScope()
    {
        var observedAtUtc = new DateTimeOffset(2026, 5, 6, 12, 0, 0, TimeSpan.Zero);
        var service = new BacktestRunFactory(
            new StaticPaperCapitalService(new PaperCapitalResponse(
                EffectiveCapital: 125000.129m,
                Currency: "usd",
                Source: PaperCapitalSources.LocalPaperLedger,
                IbkrAvailable: DisabledIbkr(),
                LocalConfigured: true,
                LocalCapital: 125000.129m,
                Messages: [])),
            new StaticPaperCapitalIdentityProvider(Identity),
            new StaticTimeProvider(observedAtUtc));

        var result = await service.CreateQueuedRunAsync(ValidRequest());

        Assert.True(result.IsSuccess);
        Assert.NotNull(result.Run);
        Assert.Null(result.Error);
        Assert.Equal(Identity.UserId, result.Run.Scope.UserId);
        Assert.Equal(Identity.WorkspaceId, result.Run.Scope.WorkspaceId);
        Assert.StartsWith("bt_", result.Run.Run.Id, StringComparison.Ordinal);
        Assert.Equal(BacktestRunStatuses.Queued, result.Run.Run.Status);
        Assert.Equal(observedAtUtc, result.Run.Run.CreatedAtUtc);
        Assert.Equal(observedAtUtc, result.Run.Run.UpdatedAtUtc);
        Assert.Equal(125000.13m, result.Run.Run.Capital.InitialCapital);
        Assert.Equal("USD", result.Run.Run.Capital.Currency);
        Assert.Equal(PaperCapitalSources.LocalPaperLedger, result.Run.Run.Capital.CapitalSource);
        Assert.Equal("AAPL", result.Run.Run.Request.Symbol.Symbol);
        Assert.Equal(BacktestStrategyIds.Breakout, result.Run.Run.Request.StrategyId);
    }

    [Fact]
    public async Task CreateQueuedRunAsync_BlocksWhenNoEffectiveCapitalIsAvailable()
    {
        var service = new BacktestRunFactory(
            new StaticPaperCapitalService(new PaperCapitalResponse(
                EffectiveCapital: null,
                Currency: "USD",
                Source: PaperCapitalSources.Unavailable,
                IbkrAvailable: DisabledIbkr(),
                LocalConfigured: false,
                LocalCapital: null,
                Messages: [])),
            new StaticPaperCapitalIdentityProvider(Identity),
            new StaticTimeProvider(DateTimeOffset.UnixEpoch));

        var result = await service.CreateQueuedRunAsync(ValidRequest());

        Assert.False(result.IsSuccess);
        Assert.Null(result.Run);
        Assert.NotNull(result.Error);
        Assert.Equal(BacktestErrorCodes.CapitalUnavailable, result.Error.Code);
        Assert.Equal(BacktestSafeMessages.CapitalUnavailable, result.Error.Message);
    }

    [Fact]
    public async Task CreateQueuedRunAsync_MapsValidationFailuresToSafeErrors()
    {
        var service = new BacktestRunFactory(
            new StaticPaperCapitalService(new PaperCapitalResponse(
                EffectiveCapital: 100000m,
                Currency: "USD",
                Source: PaperCapitalSources.LocalPaperLedger,
                IbkrAvailable: DisabledIbkr(),
                LocalConfigured: true,
                LocalCapital: 100000m,
                Messages: [])),
            new StaticPaperCapitalIdentityProvider(Identity),
            new StaticTimeProvider(DateTimeOffset.UnixEpoch));

        var result = await service.CreateQueuedRunAsync(ValidRequest(strategyId: "custom-code"));

        Assert.False(result.IsSuccess);
        Assert.NotNull(result.Error);
        Assert.Equal(BacktestErrorCodes.UnsupportedStrategy, result.Error.Code);
        Assert.Null(result.Run);
    }

    private static BacktestCreateRequest ValidRequest(string strategyId = BacktestStrategyIds.Breakout) => new(
        Symbol: MarketDataSymbolIdentity.Create("AAPL", "ibkr", "265598", MarketDataAssetClasses.Stock, "NASDAQ", "USD"),
        SymbolCode: null,
        StrategyId: strategyId,
        Parameters: null,
        ChartRange: ChartRangePresets.SixMonths,
        CostModel: null,
        SlippageBps: null,
        BenchmarkMode: null);

    private static IbkrPaperCapitalAvailability DisabledIbkr() => IbkrPaperCapitalAvailability.Unavailable(
        PaperCapitalAvailabilityStates.Disabled,
        PaperCapitalErrorCodes.IbkrDisabled,
        PaperCapitalSafeMessages.IbkrSourceUnavailable,
        severity: PaperCapitalMessageSeverity.Info);

    private sealed class StaticPaperCapitalIdentityProvider(PaperCapitalIdentity identity) : IPaperCapitalIdentityProvider
    {
        public PaperCapitalIdentity Current { get; } = identity;
    }

    private sealed class StaticPaperCapitalService(PaperCapitalResponse response) : IPaperCapitalService
    {
        public Task<PaperCapitalResponse> GetAsync(CancellationToken cancellationToken = default) => Task.FromResult(response);

        public Task<PaperCapitalIntakeResult> UpdateLocalAsync(LocalPaperCapitalUpdateRequest? request, CancellationToken cancellationToken = default) =>
            Task.FromResult(PaperCapitalIntakeResult.Success(response));
    }

    private sealed class StaticTimeProvider(DateTimeOffset utcNow) : TimeProvider
    {
        public override DateTimeOffset GetUtcNow() => utcNow;
    }
}
