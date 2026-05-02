using ATrade.Workspaces;

namespace ATrade.Workspaces.Tests;

public sealed class WorkspaceWatchlistIntakeTests
{
    [Fact]
    public async Task LoadInitializesSchemaAndUsesCurrentIdentity()
    {
        var identity = WorkspaceIdentity.Create("user-1", "workspace-1");
        var schema = new FakeSchemaInitializer();
        var repository = new FakeWorkspaceWatchlistRepository();
        var intake = CreateIntake(identity, schema, repository);

        var result = await intake.GetAsync();

        Assert.True(result.IsSuccess);
        Assert.Null(result.Error);
        Assert.Equal(1, schema.InitializeCount);
        Assert.Equal(identity, repository.LastGetIdentity);
        Assert.Equal(identity.UserId, result.Response?.UserId);
        Assert.Equal(identity.WorkspaceId, result.Response?.WorkspaceId);
    }

    [Fact]
    public async Task PinNormalizesExactInstrumentInputBeforeRepositoryCall()
    {
        var identity = WorkspaceIdentity.Create("user-1", "workspace-1");
        var schema = new FakeSchemaInitializer();
        var repository = new FakeWorkspaceWatchlistRepository();
        var intake = CreateIntake(identity, schema, repository);

        var result = await intake.PinAsync(new WorkspaceWatchlistSymbolInput(
            Symbol: " aapl ",
            Provider: " IBKR ",
            ProviderSymbolId: " 265598 ",
            IbkrConid: 265598,
            Name: " Apple Inc. ",
            Exchange: " nasdaq ",
            Currency: " usd ",
            AssetClass: " stock "));

        Assert.True(result.IsSuccess);
        Assert.Equal(1, schema.InitializeCount);
        Assert.Equal(identity, repository.LastPinIdentity);
        Assert.NotNull(repository.LastPinnedSymbol);
        Assert.Equal("AAPL", repository.LastPinnedSymbol.Symbol);
        Assert.Equal("ibkr", repository.LastPinnedSymbol.Provider);
        Assert.Equal("265598", repository.LastPinnedSymbol.ProviderSymbolId);
        Assert.Equal(265598, repository.LastPinnedSymbol.IbkrConid);
        Assert.Equal("Apple Inc.", repository.LastPinnedSymbol.Name);
        Assert.Equal("NASDAQ", repository.LastPinnedSymbol.Exchange);
        Assert.Equal("USD", repository.LastPinnedSymbol.Currency);
        Assert.Equal("STK", repository.LastPinnedSymbol.AssetClass);
    }

    [Fact]
    public async Task ReplaceNormalizesAndDeduplicatesExactInstrumentPinsBeforeRepositoryCall()
    {
        var identity = WorkspaceIdentity.Create("user-1", "workspace-1");
        var schema = new FakeSchemaInitializer();
        var repository = new FakeWorkspaceWatchlistRepository();
        var intake = CreateIntake(identity, schema, repository);

        var result = await intake.ReplaceAsync(new ReplaceWorkspaceWatchlistRequest(new[]
        {
            new WorkspaceWatchlistSymbolInput("msft"),
            new WorkspaceWatchlistSymbolInput("AAPL", Provider: "ibkr", ProviderSymbolId: "265598", IbkrConid: 265598, Name: "Apple Inc.", Exchange: "NASDAQ"),
            new WorkspaceWatchlistSymbolInput(" aapl ", Provider: "IBKR", ProviderSymbolId: " 265598 ", IbkrConid: 265598, Name: "Apple Inc. Class A", Exchange: "nasdaq"),
            new WorkspaceWatchlistSymbolInput("AAPL", Provider: "manual", Name: "Manual Apple"),
        }));

        Assert.True(result.IsSuccess);
        Assert.Equal(1, schema.InitializeCount);
        Assert.Equal(identity, repository.LastReplaceIdentity);
        Assert.NotNull(repository.LastReplacementSymbols);
        Assert.Collection(
            repository.LastReplacementSymbols,
            symbol =>
            {
                Assert.Equal("MSFT", symbol.Symbol);
                Assert.Equal("manual", symbol.Provider);
                Assert.Null(symbol.ProviderSymbolId);
            },
            symbol =>
            {
                Assert.Equal("AAPL", symbol.Symbol);
                Assert.Equal("ibkr", symbol.Provider);
                Assert.Equal("265598", symbol.ProviderSymbolId);
                Assert.Equal("Apple Inc. Class A", symbol.Name);
            },
            symbol =>
            {
                Assert.Equal("AAPL", symbol.Symbol);
                Assert.Equal("manual", symbol.Provider);
                Assert.Equal("Manual Apple", symbol.Name);
            });
    }

    [Fact]
    public async Task ExactUnpinValidatesAndNormalizesInstrumentKeyBeforeRepositoryCall()
    {
        var identity = WorkspaceIdentity.Create("user-1", "workspace-1");
        var schema = new FakeSchemaInitializer();
        var repository = new FakeWorkspaceWatchlistRepository();
        var intake = CreateIntake(identity, schema, repository);
        var instrumentKey = WorkspaceWatchlistInstrumentKey.Create(
            "AAPL",
            "ibkr",
            "265598",
            265598,
            "NASDAQ",
            "USD",
            "STK");

        var result = await intake.UnpinByInstrumentKeyAsync($"  {instrumentKey}  ");

        Assert.True(result.IsSuccess);
        Assert.Equal(1, schema.InitializeCount);
        Assert.Equal(identity, repository.LastUnpinInstrumentIdentity);
        Assert.Equal(instrumentKey, repository.LastUnpinnedInstrumentKey);
    }

    [Fact]
    public async Task AmbiguousLegacyUnpinReturnsStableValidationError()
    {
        var identity = WorkspaceIdentity.Create("user-1", "workspace-1");
        var schema = new FakeSchemaInitializer();
        var repository = new FakeWorkspaceWatchlistRepository
        {
            UnpinHandler = (_, symbol, _) => throw new WorkspaceWatchlistValidationException(
                WorkspaceWatchlistErrorCodes.AmbiguousSymbol,
                $"Symbol '{symbol}' has multiple market-specific pins. Remove one by instrumentKey instead.")
        };
        var intake = CreateIntake(identity, schema, repository);

        var result = await intake.UnpinBySymbolAsync(" aapl ");

        Assert.False(result.IsSuccess);
        Assert.Equal(1, schema.InitializeCount);
        Assert.Equal("AAPL", repository.LastUnpinnedSymbol);
        Assert.NotNull(result.Error);
        Assert.Equal(WorkspaceWatchlistIntakeErrorKind.Validation, result.Error.Kind);
        Assert.Equal(WorkspaceWatchlistErrorCodes.AmbiguousSymbol, result.Error.Code);
        Assert.Contains("instrumentKey", result.Error.Error, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task InvalidInputReturnsStableErrorsBeforeSchemaInitialization()
    {
        var schema = new FakeSchemaInitializer();
        var repository = new FakeWorkspaceWatchlistRepository();
        var intake = CreateIntake(WorkspaceIdentityDefaults.LocalPaperTradingWorkspace, schema, repository);

        var missingPayload = await intake.PinAsync(null);
        var missingInstrumentKey = await intake.UnpinByInstrumentKeyAsync("  ");

        Assert.False(missingPayload.IsSuccess);
        Assert.Equal(WorkspaceWatchlistErrorCodes.InvalidSymbol, missingPayload.Error?.Code);
        Assert.Contains("payload", missingPayload.Error?.Error, StringComparison.OrdinalIgnoreCase);
        Assert.False(missingInstrumentKey.IsSuccess);
        Assert.Equal(WorkspaceWatchlistErrorCodes.InvalidInstrumentKey, missingInstrumentKey.Error?.Code);
        Assert.Equal(0, schema.InitializeCount);
        Assert.Null(repository.LastPinnedSymbol);
        Assert.Null(repository.LastUnpinnedInstrumentKey);
    }

    [Fact]
    public async Task StorageUnavailableReturnsStableErrorShape()
    {
        var schema = new FakeSchemaInitializer();
        var repository = new FakeWorkspaceWatchlistRepository
        {
            GetHandler = (_, _) => throw new WorkspaceStorageUnavailableException("database details should stay internal"),
        };
        var intake = CreateIntake(WorkspaceIdentityDefaults.LocalPaperTradingWorkspace, schema, repository);

        var result = await intake.GetAsync();

        Assert.False(result.IsSuccess);
        Assert.Equal(1, schema.InitializeCount);
        Assert.NotNull(result.Error);
        Assert.Equal(WorkspaceWatchlistIntakeErrorKind.StorageUnavailable, result.Error.Kind);
        Assert.Equal(WorkspaceWatchlistErrorCodes.StorageUnavailable, result.Error.Code);
        Assert.Equal("Watchlist storage is unavailable.", result.Error.Error);
    }

    private static WorkspaceWatchlistIntake CreateIntake(
        WorkspaceIdentity identity,
        FakeSchemaInitializer schema,
        FakeWorkspaceWatchlistRepository repository) => new(
            new FakeWorkspaceIdentityProvider(identity),
            schema,
            repository);

    private static WorkspaceWatchlistResponse EmptyResponse(WorkspaceIdentity identity) => new(
        identity.UserId,
        identity.WorkspaceId,
        Array.Empty<WorkspaceWatchlistSymbol>());

    private sealed class FakeWorkspaceIdentityProvider(WorkspaceIdentity identity) : IWorkspaceIdentityProvider
    {
        public WorkspaceIdentity Current { get; } = identity;
    }

    private sealed class FakeSchemaInitializer : IWorkspaceWatchlistSchemaInitializer
    {
        public int InitializeCount { get; private set; }

        public Task InitializeAsync(CancellationToken cancellationToken = default)
        {
            cancellationToken.ThrowIfCancellationRequested();
            InitializeCount++;
            return Task.CompletedTask;
        }
    }

    private sealed class FakeWorkspaceWatchlistRepository : IWorkspaceWatchlistRepository
    {
        public WorkspaceIdentity? LastGetIdentity { get; private set; }

        public WorkspaceIdentity? LastPinIdentity { get; private set; }

        public WorkspaceWatchlistSymbolInput? LastPinnedSymbol { get; private set; }

        public WorkspaceIdentity? LastReplaceIdentity { get; private set; }

        public IReadOnlyList<WorkspaceWatchlistSymbolInput>? LastReplacementSymbols { get; private set; }

        public WorkspaceIdentity? LastUnpinSymbolIdentity { get; private set; }

        public string? LastUnpinnedSymbol { get; private set; }

        public WorkspaceIdentity? LastUnpinInstrumentIdentity { get; private set; }

        public string? LastUnpinnedInstrumentKey { get; private set; }

        public Func<WorkspaceIdentity, CancellationToken, Task<WorkspaceWatchlistResponse>> GetHandler { get; init; } =
            (identity, _) => Task.FromResult(EmptyResponse(identity));

        public Func<WorkspaceIdentity, WorkspaceWatchlistSymbolInput, CancellationToken, Task<WorkspaceWatchlistResponse>> PinHandler { get; init; } =
            (identity, _, _) => Task.FromResult(EmptyResponse(identity));

        public Func<WorkspaceIdentity, IReadOnlyList<WorkspaceWatchlistSymbolInput>, CancellationToken, Task<WorkspaceWatchlistResponse>> ReplaceHandler { get; init; } =
            (identity, _, _) => Task.FromResult(EmptyResponse(identity));

        public Func<WorkspaceIdentity, string, CancellationToken, Task<WorkspaceWatchlistResponse>> UnpinHandler { get; init; } =
            (identity, _, _) => Task.FromResult(EmptyResponse(identity));

        public Func<WorkspaceIdentity, string, CancellationToken, Task<WorkspaceWatchlistResponse>> UnpinByInstrumentKeyHandler { get; init; } =
            (identity, _, _) => Task.FromResult(EmptyResponse(identity));

        public Task<WorkspaceWatchlistResponse> GetAsync(WorkspaceIdentity identity, CancellationToken cancellationToken = default)
        {
            cancellationToken.ThrowIfCancellationRequested();
            LastGetIdentity = identity;
            return GetHandler(identity, cancellationToken);
        }

        public Task<WorkspaceWatchlistResponse> PinAsync(
            WorkspaceIdentity identity,
            WorkspaceWatchlistSymbolInput symbol,
            CancellationToken cancellationToken = default)
        {
            cancellationToken.ThrowIfCancellationRequested();
            LastPinIdentity = identity;
            LastPinnedSymbol = symbol;
            return PinHandler(identity, symbol, cancellationToken);
        }

        public Task<WorkspaceWatchlistResponse> ReplaceAsync(
            WorkspaceIdentity identity,
            IReadOnlyList<WorkspaceWatchlistSymbolInput> symbols,
            CancellationToken cancellationToken = default)
        {
            cancellationToken.ThrowIfCancellationRequested();
            LastReplaceIdentity = identity;
            LastReplacementSymbols = symbols;
            return ReplaceHandler(identity, symbols, cancellationToken);
        }

        public Task<WorkspaceWatchlistResponse> UnpinAsync(
            WorkspaceIdentity identity,
            string symbol,
            CancellationToken cancellationToken = default)
        {
            cancellationToken.ThrowIfCancellationRequested();
            LastUnpinSymbolIdentity = identity;
            LastUnpinnedSymbol = symbol;
            return UnpinHandler(identity, symbol, cancellationToken);
        }

        public Task<WorkspaceWatchlistResponse> UnpinByInstrumentKeyAsync(
            WorkspaceIdentity identity,
            string instrumentKey,
            CancellationToken cancellationToken = default)
        {
            cancellationToken.ThrowIfCancellationRequested();
            LastUnpinInstrumentIdentity = identity;
            LastUnpinnedInstrumentKey = instrumentKey;
            return UnpinByInstrumentKeyHandler(identity, instrumentKey, cancellationToken);
        }
    }
}
