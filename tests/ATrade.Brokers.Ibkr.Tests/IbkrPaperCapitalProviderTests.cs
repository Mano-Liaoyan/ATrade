using ATrade.Accounts;
using Microsoft.Extensions.Logging.Abstractions;

namespace ATrade.Brokers.Ibkr.Tests;

public sealed class IbkrPaperCapitalProviderTests
{
    private const string SensitiveAccountId = "PAPER_TEST_ACCOUNT";

    [Fact]
    public async Task GetAvailabilityAsync_ReturnsAuthenticatedPaperBalance()
    {
        var service = CreateProvider(
            ReadyReadiness(),
            new FakeAccountSummaryClient(new IbkrAccountSummaryBalance(123456.78m, "usd", "totalcashvalue")));

        var availability = await service.GetAvailabilityAsync();

        Assert.True(availability.Available);
        Assert.Equal(PaperCapitalAvailabilityStates.Available, availability.State);
        Assert.Equal(123456.78m, availability.Capital);
        Assert.Equal("USD", availability.Currency);
        Assert.DoesNotContain(availability.Messages, message => ContainsSensitiveValue(message.Message));
    }

    [Theory]
    [MemberData(nameof(UnavailableReadinessCases))]
    public async Task GetAvailabilityAsync_MapsReadinessStatesToSafeUnavailableStates(
        IbkrSessionReadinessResult readiness,
        string expectedState,
        string expectedCode)
    {
        var summaryClient = new FakeAccountSummaryClient(new IbkrAccountSummaryBalance(1000m, "USD", "totalcashvalue"));
        var service = CreateProvider(readiness, summaryClient);

        var availability = await service.GetAvailabilityAsync();

        Assert.False(availability.Available);
        Assert.Null(availability.Capital);
        Assert.Equal(expectedState, availability.State);
        Assert.Contains(availability.Messages, message => message.Code == expectedCode);
        Assert.Equal(0, summaryClient.CallCount);
        AssertRedacted(availability);
    }

    [Fact]
    public async Task GetAvailabilityAsync_MapsBalanceTimeoutToSafeUnavailableStateAndRedactsDiagnostics()
    {
        var service = CreateProvider(
            ReadyReadiness(),
            new FakeAccountSummaryClient(new TaskCanceledException($"timeout for {SensitiveAccountId} at https://127.0.0.1:5000 token=abc123")));

        var availability = await service.GetAvailabilityAsync();

        Assert.False(availability.Available);
        Assert.Equal(PaperCapitalAvailabilityStates.Timeout, availability.State);
        Assert.Contains(availability.Messages, message => message.Code == PaperCapitalErrorCodes.IbkrTimeout);
        AssertRedacted(availability);
    }

    [Fact]
    public async Task GetAvailabilityAsync_MapsProviderFailureToSafeUnavailableStateAndRedactsMessages()
    {
        var service = CreateProvider(
            ReadyReadiness(),
            new FakeAccountSummaryClient(new HttpRequestException($"account {SensitiveAccountId} failed at https://127.0.0.1:5000 cookie=abc")));

        var availability = await service.GetAvailabilityAsync();

        Assert.False(availability.Available);
        Assert.Equal(PaperCapitalAvailabilityStates.ProviderUnavailable, availability.State);
        Assert.Contains(availability.Messages, message => message.Code == PaperCapitalErrorCodes.IbkrUnavailable);
        AssertRedacted(availability);
    }

    public static IEnumerable<object[]> UnavailableReadinessCases()
    {
        yield return
        [
            IbkrSessionReadinessResult.Create(
                DisabledOptions(),
                IbkrSessionReadinessStates.Disabled,
                $"disabled for {SensitiveAccountId}"),
            PaperCapitalAvailabilityStates.Disabled,
            PaperCapitalErrorCodes.IbkrDisabled,
        ];
        yield return
        [
            IbkrSessionReadinessResult.Create(
                MissingCredentialsOptions(),
                IbkrSessionReadinessStates.CredentialsMissing,
                $"missing credentials for {SensitiveAccountId}"),
            PaperCapitalAvailabilityStates.CredentialsMissing,
            PaperCapitalErrorCodes.IbkrCredentialsMissing,
        ];
        yield return
        [
            IbkrSessionReadinessResult.Create(
                ReadyOptions(),
                IbkrSessionReadinessStates.Connecting,
                $"login required for {SensitiveAccountId}",
                authenticated: false,
                connected: true),
            PaperCapitalAvailabilityStates.Unauthenticated,
            PaperCapitalErrorCodes.IbkrUnauthenticated,
        ];
        yield return
        [
            IbkrSessionReadinessResult.Create(
                LiveOptions(),
                IbkrSessionReadinessStates.RejectedLiveMode,
                $"live mode rejected for {SensitiveAccountId}"),
            PaperCapitalAvailabilityStates.RejectedLive,
            PaperCapitalErrorCodes.IbkrRejectedLive,
        ];
        yield return
        [
            IbkrSessionReadinessResult.Create(
                ReadyOptions(),
                IbkrSessionReadinessStates.IbeamContainerConfigured,
                $"provider unavailable for {SensitiveAccountId}"),
            PaperCapitalAvailabilityStates.ProviderUnavailable,
            PaperCapitalErrorCodes.IbkrUnavailable,
        ];
    }

    private static IbkrPaperCapitalProvider CreateProvider(
        IbkrSessionReadinessResult readiness,
        IIbkrAccountSummaryClient accountSummaryClient) =>
        new(
            ReadyOptions(),
            new StaticReadinessService(readiness),
            accountSummaryClient,
            NullLogger<IbkrPaperCapitalProvider>.Instance);

    private static IbkrSessionReadinessResult ReadyReadiness() =>
        IbkrSessionReadinessResult.Create(
            ReadyOptions(),
            IbkrSessionReadinessStates.Authenticated,
            "ready",
            authenticated: true,
            connected: true);

    private static IbkrGatewayOptions ReadyOptions() => new()
    {
        IntegrationEnabled = true,
        AccountMode = IbkrAccountMode.Paper,
        GatewayBaseUrl = new Uri("https://127.0.0.1:5000"),
        PaperAccountId = SensitiveAccountId,
        Username = "paper-user",
        Password = "paper-password",
        GatewayContainer = new IbkrGatewayContainerOptions
        {
            Image = IbkrGatewayContainerOptions.DefaultIbeamImage,
            Port = 5000,
        },
    };

    private static IbkrGatewayOptions DisabledOptions()
    {
        var options = ReadyOptions();
        options.IntegrationEnabled = false;
        return options;
    }

    private static IbkrGatewayOptions MissingCredentialsOptions()
    {
        var options = ReadyOptions();
        options.Username = IbkrGatewayPlaceholderValues.Username;
        options.Password = IbkrGatewayPlaceholderValues.Password;
        options.PaperAccountId = IbkrGatewayPlaceholderValues.PaperAccountId;
        return options;
    }

    private static IbkrGatewayOptions LiveOptions()
    {
        var options = ReadyOptions();
        options.AccountMode = IbkrAccountMode.Live;
        return options;
    }

    private static void AssertRedacted(IbkrPaperCapitalAvailability availability)
    {
        Assert.DoesNotContain(SensitiveAccountId, availability.State, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("https://", availability.State, StringComparison.OrdinalIgnoreCase);
        foreach (var message in availability.Messages)
        {
            Assert.False(ContainsSensitiveValue(message.Code), message.Code);
            Assert.False(ContainsSensitiveValue(message.Message), message.Message);
        }
    }

    private static bool ContainsSensitiveValue(string? value) =>
        value?.Contains(SensitiveAccountId, StringComparison.OrdinalIgnoreCase) == true ||
        value?.Contains("paper-password", StringComparison.OrdinalIgnoreCase) == true ||
        value?.Contains("token=abc", StringComparison.OrdinalIgnoreCase) == true ||
        value?.Contains("cookie=abc", StringComparison.OrdinalIgnoreCase) == true ||
        value?.Contains("https://", StringComparison.OrdinalIgnoreCase) == true;

    private sealed class StaticReadinessService(IbkrSessionReadinessResult readiness) : IIbkrSessionReadinessService
    {
        public Task<IbkrSessionReadinessResult> CheckReadinessAsync(CancellationToken cancellationToken = default) => Task.FromResult(readiness);
    }

    private sealed class FakeAccountSummaryClient : IIbkrAccountSummaryClient
    {
        private readonly IbkrAccountSummaryBalance? balance;
        private readonly Exception? exception;

        public FakeAccountSummaryClient(IbkrAccountSummaryBalance balance)
        {
            this.balance = balance;
        }

        public FakeAccountSummaryClient(Exception exception)
        {
            this.exception = exception;
        }

        public int CallCount { get; private set; }

        public Task<IbkrAccountSummaryBalance> GetConfiguredPaperAccountBalanceAsync(CancellationToken cancellationToken = default)
        {
            CallCount++;
            if (exception is not null)
            {
                throw exception;
            }

            return Task.FromResult(balance!);
        }
    }
}
