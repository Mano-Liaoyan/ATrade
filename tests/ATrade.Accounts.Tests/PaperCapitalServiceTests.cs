using ATrade.Accounts;

namespace ATrade.Accounts.Tests;

public sealed class PaperCapitalServiceTests
{
    private const string SensitiveAccountId = "DU1234567";
    private static readonly PaperCapitalIdentity Identity = PaperCapitalIdentityDefaults.LocalPaperTradingWorkspace;

    [Fact]
    public async Task GetAsync_ReturnsUnavailableWhenNeitherIbkrNorLocalCapitalExists()
    {
        var service = CreateService(new InMemoryLocalPaperCapitalRepository(), DisabledIbkr());

        var response = await service.GetAsync();

        Assert.Null(response.EffectiveCapital);
        Assert.Equal(PaperCapitalSources.Unavailable, response.Source);
        Assert.False(response.IbkrAvailable.Available);
        Assert.False(response.LocalConfigured);
        Assert.Null(response.LocalCapital);
        Assert.Contains(response.Messages, message => message.Code == PaperCapitalErrorCodes.NoCapitalSource);
        AssertRedacted(response);
    }

    [Fact]
    public async Task UpdateLocalAsync_PersistsValidatedCapitalAndReturnsLocalFallback()
    {
        var repository = new InMemoryLocalPaperCapitalRepository();
        var service = CreateService(repository, DisabledIbkr());

        var result = await service.UpdateLocalAsync(new LocalPaperCapitalUpdateRequest(25000.129m, "usd"));

        Assert.True(result.Succeeded);
        Assert.NotNull(result.Response);
        Assert.Equal(PaperCapitalSources.LocalPaperLedger, result.Response.Source);
        Assert.Equal(25000.13m, result.Response.EffectiveCapital);
        Assert.Equal("USD", result.Response.Currency);
        Assert.Equal(25000.13m, result.Response.LocalCapital);
        Assert.True(result.Response.LocalConfigured);
        Assert.Equal(Identity, repository.LastIdentity);
        AssertRedacted(result.Response);
    }

    [Fact]
    public async Task GetAsync_PrefersAvailableIbkrPaperBalanceOverConfiguredLocalFallback()
    {
        var repository = new InMemoryLocalPaperCapitalRepository();
        await repository.UpsertAsync(Identity, new LocalPaperCapitalValue(10000m, "USD"));
        var ibkr = new StaticIbkrPaperCapitalProvider(new IbkrPaperCapitalAvailability(
            true,
            PaperCapitalAvailabilityStates.Available,
            75000m,
            "USD",
            []));
        var service = CreateService(repository, ibkr);

        var response = await service.GetAsync();

        Assert.Equal(PaperCapitalSources.IbkrPaperBalance, response.Source);
        Assert.Equal(75000m, response.EffectiveCapital);
        Assert.Equal(10000m, response.LocalCapital);
        Assert.True(response.IbkrAvailable.Available);
        AssertRedacted(response);
    }

    [Fact]
    public async Task UpdateLocalAsync_ReturnsStableStorageUnavailableErrorWithoutLeakingExceptionDetails()
    {
        var service = CreateService(new ThrowingLocalPaperCapitalRepository("Host=localhost;Username=postgres;Password=secret"), DisabledIbkr());

        var result = await service.UpdateLocalAsync(new LocalPaperCapitalUpdateRequest(50000m, "USD"));

        Assert.False(result.Succeeded);
        Assert.Null(result.Response);
        Assert.NotNull(result.Error);
        Assert.Equal(PaperCapitalErrorCodes.StorageUnavailable, result.Error.Code);
        Assert.Equal(PaperCapitalSafeMessages.LocalStorageUnavailable, result.Error.Message);
        Assert.DoesNotContain("localhost", result.Error.Message, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("postgres", result.Error.Message, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("secret", result.Error.Message, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task UpdateLocalAsync_ReturnsValidationFailureForInvalidPayload()
    {
        var service = CreateService(new InMemoryLocalPaperCapitalRepository(), DisabledIbkr());

        var result = await service.UpdateLocalAsync(new LocalPaperCapitalUpdateRequest(-10m, "USD"));

        Assert.False(result.Succeeded);
        Assert.NotNull(result.Error);
        Assert.Equal(PaperCapitalErrorCodes.InvalidAmount, result.Error.Code);
    }

    [Fact]
    public void ResponseAndUpdateContracts_DoNotExposeAccountOrCredentialFields()
    {
        Assert.DoesNotContain(typeof(PaperCapitalResponse).GetProperties(), property => IsSensitiveProperty(property.Name));
        Assert.DoesNotContain(typeof(LocalPaperCapitalUpdateRequest).GetProperties(), property => IsSensitiveProperty(property.Name));
        Assert.DoesNotContain(typeof(IbkrPaperCapitalAvailability).GetProperties(), property => IsSensitiveProperty(property.Name));
        Assert.DoesNotContain(typeof(LocalPaperCapitalState).GetProperties(), property => IsSensitiveProperty(property.Name));
    }

    private static PaperCapitalService CreateService(
        ILocalPaperCapitalRepository repository,
        params IIbkrPaperCapitalProvider[] ibkrProviders) =>
        new(repository, new StaticPaperCapitalIdentityProvider(Identity), new NoopLocalPaperCapitalSchemaInitializer(), ibkrProviders);

    private static IIbkrPaperCapitalProvider DisabledIbkr() =>
        new StaticIbkrPaperCapitalProvider(IbkrPaperCapitalAvailability.Unavailable(
            PaperCapitalAvailabilityStates.Disabled,
            PaperCapitalErrorCodes.IbkrDisabled,
            $"IBKR paper balance is unavailable for account {SensitiveAccountId}."));

    private static bool IsSensitiveProperty(string name) =>
        name.Contains("Account", StringComparison.OrdinalIgnoreCase) ||
        name.Contains("Credential", StringComparison.OrdinalIgnoreCase) ||
        name.Contains("Password", StringComparison.OrdinalIgnoreCase) ||
        name.Contains("Token", StringComparison.OrdinalIgnoreCase) ||
        name.Contains("Gateway", StringComparison.OrdinalIgnoreCase) ||
        name.Contains("Session", StringComparison.OrdinalIgnoreCase);

    private static void AssertRedacted(PaperCapitalResponse response)
    {
        AssertDoesNotContainSensitiveValue(response.Source);
        AssertDoesNotContainSensitiveValue(response.Currency);
        foreach (var message in response.Messages)
        {
            AssertDoesNotContainSensitiveValue(message.Code);
            AssertDoesNotContainSensitiveValue(message.Message);
        }

        foreach (var message in response.IbkrAvailable.Messages)
        {
            AssertDoesNotContainSensitiveValue(message.Code);
            AssertDoesNotContainSensitiveValue(message.Message);
        }
    }

    private static void AssertDoesNotContainSensitiveValue(string? value)
    {
        Assert.DoesNotContain(SensitiveAccountId, value, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("password", value, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("secret", value, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("token", value, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("https://", value, StringComparison.OrdinalIgnoreCase);
    }

    private sealed class StaticPaperCapitalIdentityProvider(PaperCapitalIdentity identity) : IPaperCapitalIdentityProvider
    {
        public PaperCapitalIdentity Current { get; } = identity;
    }

    private sealed class NoopLocalPaperCapitalSchemaInitializer : ILocalPaperCapitalSchemaInitializer
    {
        public Task InitializeAsync(CancellationToken cancellationToken = default) => Task.CompletedTask;
    }

    private sealed class StaticIbkrPaperCapitalProvider(IbkrPaperCapitalAvailability availability) : IIbkrPaperCapitalProvider
    {
        public Task<IbkrPaperCapitalAvailability> GetAvailabilityAsync(CancellationToken cancellationToken = default) => Task.FromResult(availability);
    }

    private sealed class InMemoryLocalPaperCapitalRepository : ILocalPaperCapitalRepository
    {
        private readonly Dictionary<PaperCapitalIdentity, LocalPaperCapitalState> states = [];

        public PaperCapitalIdentity? LastIdentity { get; private set; }

        public Task<LocalPaperCapitalState> GetAsync(PaperCapitalIdentity identity, CancellationToken cancellationToken = default)
        {
            LastIdentity = identity;
            return Task.FromResult(states.GetValueOrDefault(identity, LocalPaperCapitalState.Unconfigured()));
        }

        public Task<LocalPaperCapitalState> UpsertAsync(
            PaperCapitalIdentity identity,
            LocalPaperCapitalValue value,
            CancellationToken cancellationToken = default)
        {
            LastIdentity = identity;
            var state = new LocalPaperCapitalState(true, value.Amount, value.Currency, DateTimeOffset.UnixEpoch);
            states[identity] = state;
            return Task.FromResult(state);
        }
    }

    private sealed class ThrowingLocalPaperCapitalRepository(string message) : ILocalPaperCapitalRepository
    {
        public Task<LocalPaperCapitalState> GetAsync(PaperCapitalIdentity identity, CancellationToken cancellationToken = default) =>
            throw new PaperCapitalStorageUnavailableException(message);

        public Task<LocalPaperCapitalState> UpsertAsync(
            PaperCapitalIdentity identity,
            LocalPaperCapitalValue value,
            CancellationToken cancellationToken = default) =>
            throw new PaperCapitalStorageUnavailableException(message);
    }
}
