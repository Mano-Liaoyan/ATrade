using ATrade.Brokers;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;

namespace ATrade.Brokers.Ibkr.Tests;

public sealed class IbkrSessionReadinessTests
{
    [Fact]
    public async Task CheckReadinessAsync_ReturnsDisabledWithoutCallingGateway()
    {
        var fakeGatewayClient = new FakeGatewayClient();
        var service = CreateService(
            new IbkrGatewayOptions
            {
                IntegrationEnabled = false,
                AccountMode = IbkrAccountMode.Paper,
            },
            fakeGatewayClient);

        var readiness = await service.CheckReadinessAsync();

        Assert.Equal(IbkrSessionReadinessStates.Disabled, readiness.State);
        Assert.Equal("IBKR integration is disabled.", readiness.Message);
        Assert.False(readiness.IsReady);
        Assert.Equal(0, fakeGatewayClient.CallCount);
    }

    [Fact]
    public async Task CheckReadinessAsync_ReturnsRejectedLiveModeWithoutCallingGateway()
    {
        var options = CreateReadyOptions();
        options.AccountMode = IbkrAccountMode.Live;
        var fakeGatewayClient = new FakeGatewayClient();
        var service = CreateService(options, fakeGatewayClient);

        var readiness = await service.CheckReadinessAsync();

        Assert.Equal(IbkrSessionReadinessStates.RejectedLiveMode, readiness.State);
        Assert.Equal(IbkrAccountMode.Live, readiness.AccountMode);
        Assert.Contains("Only Paper is supported", readiness.Message);
        Assert.False(readiness.CanAttemptLocalGatewayRead);
        Assert.Equal(0, fakeGatewayClient.CallCount);
    }

    [Fact]
    public async Task CheckReadinessAsync_ReturnsCredentialsMissingWhenPlaceholdersAreConfigured()
    {
        var options = CreateReadyOptions();
        options.PaperAccountId = IbkrGatewayPlaceholderValues.PaperAccountId;
        options.Username = IbkrGatewayPlaceholderValues.Username;
        options.Password = IbkrGatewayPlaceholderValues.Password;
        var fakeGatewayClient = new FakeGatewayClient();
        var service = CreateService(options, fakeGatewayClient);

        var readiness = await service.CheckReadinessAsync();

        Assert.Equal(IbkrSessionReadinessStates.CredentialsMissing, readiness.State);
        Assert.False(readiness.HasConfiguredCredentials);
        Assert.False(readiness.HasPaperAccountId);
        Assert.Contains("ignored local .env", readiness.Message);
        Assert.DoesNotContain(IbkrGatewayPlaceholderValues.PaperAccountId, readiness.Message);
        Assert.DoesNotContain(IbkrGatewayPlaceholderValues.Username, readiness.Message);
        Assert.DoesNotContain(IbkrGatewayPlaceholderValues.Password, readiness.Message);
        Assert.Equal(0, fakeGatewayClient.CallCount);
    }

    [Fact]
    public async Task CheckReadinessAsync_ReturnsNotConfiguredWhenIbeamContainerContractIsMissing()
    {
        var options = CreateReadyOptions();
        options.GatewayContainer.Image = "example.invalid/ibkr-gateway-paper:local";
        options.GatewayContainer.Port = 5000;
        var fakeGatewayClient = new FakeGatewayClient();
        var service = CreateService(options, fakeGatewayClient);

        var readiness = await service.CheckReadinessAsync();

        Assert.Equal(IbkrSessionReadinessStates.NotConfigured, readiness.State);
        Assert.False(readiness.HasConfiguredIbeamContainer);
        Assert.Contains(IbkrGatewayContainerOptions.DefaultIbeamImage, readiness.Message);
        Assert.Equal(0, fakeGatewayClient.CallCount);
    }

    [Fact]
    public async Task CheckReadinessAsync_ReturnsNotConfiguredWhenGatewayUrlIsMissing()
    {
        var options = CreateReadyOptions();
        options.GatewayBaseUrl = null;
        var fakeGatewayClient = new FakeGatewayClient();
        var service = CreateService(options, fakeGatewayClient);

        var readiness = await service.CheckReadinessAsync();

        Assert.Equal(IbkrSessionReadinessStates.NotConfigured, readiness.State);
        Assert.False(readiness.HasGatewayBaseUrl);
        Assert.Contains(IbkrGatewayEnvironmentVariables.GatewayUrl, readiness.Message);
        Assert.Equal(0, fakeGatewayClient.CallCount);
    }

    [Fact]
    public async Task CheckReadinessAsync_MapsConfiguredIbeamWhenEndpointIsUnreachableAndRedactsDiagnostic()
    {
        var options = CreateReadyOptions();
        var fakeGatewayClient = new FakeGatewayClient
        {
            Exception = new HttpRequestException("connection refused for paper-user with paper-password at https://127.0.0.1:5000 account DU1234567 token=abc123"),
        };
        var service = CreateService(options, fakeGatewayClient);

        var readiness = await service.CheckReadinessAsync();

        Assert.Equal(IbkrSessionReadinessStates.IbeamContainerConfigured, readiness.State);
        Assert.Contains("local Client Portal HTTPS transport", readiness.Message);
        Assert.Contains("retry", readiness.Message);
        Assert.NotNull(readiness.Diagnostic);
        Assert.Contains("[redacted]", readiness.Diagnostic);
        Assert.DoesNotContain("paper-user", readiness.Diagnostic);
        Assert.DoesNotContain("paper-password", readiness.Diagnostic);
        Assert.DoesNotContain("DU1234567", readiness.Diagnostic);
        Assert.DoesNotContain("127.0.0.1", readiness.Diagnostic);
        Assert.DoesNotContain("abc123", readiness.Diagnostic);
        Assert.Equal(1, fakeGatewayClient.CallCount);
    }

    [Fact]
    public async Task CheckReadinessAsync_MapsUnauthenticatedConnectedGatewaySession()
    {
        var fakeGatewayClient = new FakeGatewayClient
        {
            SessionStatus = new IbkrGatewaySessionStatus(
                Authenticated: false,
                Connected: true,
                Competing: false,
                Message: "login required",
                ServerName: "paper-gateway",
                ServerVersion: "10.27.1"),
        };
        var service = CreateService(CreateReadyOptions(), fakeGatewayClient);

        var readiness = await service.CheckReadinessAsync();

        Assert.Equal(IbkrSessionReadinessStates.Connecting, readiness.State);
        Assert.False(readiness.Authenticated);
        Assert.True(readiness.Connected);
        Assert.False(readiness.IsReady);
        Assert.Equal("login required", readiness.Message);
        Assert.Equal(1, fakeGatewayClient.CallCount);
    }

    [Fact]
    public async Task CheckReadinessAsync_MapsAuthenticatedGatewaySession()
    {
        var fakeGatewayClient = new FakeGatewayClient
        {
            SessionStatus = new IbkrGatewaySessionStatus(
                Authenticated: true,
                Connected: true,
                Competing: false,
                Message: "ready",
                ServerName: "paper-gateway",
                ServerVersion: "10.27.1"),
        };
        var service = CreateService(CreateReadyOptions(), fakeGatewayClient);

        var readiness = await service.CheckReadinessAsync();

        Assert.Equal(IbkrSessionReadinessStates.Authenticated, readiness.State);
        Assert.True(readiness.Authenticated);
        Assert.True(readiness.Connected);
        Assert.True(readiness.IsReady);
        Assert.True(readiness.CanAttemptLocalGatewayRead);
        Assert.Equal("ready", readiness.Message);
        Assert.Equal(1, fakeGatewayClient.CallCount);
    }

    [Fact]
    public async Task CheckReadinessAsync_MapsDisconnectedGatewaySessionAsDegraded()
    {
        var fakeGatewayClient = new FakeGatewayClient
        {
            SessionStatus = new IbkrGatewaySessionStatus(
                Authenticated: false,
                Connected: false,
                Competing: true,
                Message: "gateway restarting",
                ServerName: null,
                ServerVersion: null),
        };
        var service = CreateService(CreateReadyOptions(), fakeGatewayClient);

        var readiness = await service.CheckReadinessAsync();

        Assert.Equal(IbkrSessionReadinessStates.Degraded, readiness.State);
        Assert.False(readiness.Authenticated);
        Assert.False(readiness.Connected);
        Assert.True(readiness.Competing);
        Assert.Equal("gateway restarting", readiness.Message);
        Assert.Equal(1, fakeGatewayClient.CallCount);
    }

    [Fact]
    public async Task CheckReadinessAsync_MapsStatusTimeoutToSafeTransportState()
    {
        var fakeGatewayClient = new FakeGatewayClient
        {
            Exception = new TaskCanceledException("timeout for paper-user at https://127.0.0.1:5000"),
        };
        var service = CreateService(CreateReadyOptions(), fakeGatewayClient);

        var readiness = await service.CheckReadinessAsync();

        Assert.Equal(IbkrSessionReadinessStates.IbeamContainerConfigured, readiness.State);
        Assert.Equal(IbkrGatewayTransport.CreateTransportTimeoutMessage(), readiness.Message);
        Assert.NotNull(readiness.Diagnostic);
        Assert.DoesNotContain("paper-user", readiness.Diagnostic);
        Assert.DoesNotContain("127.0.0.1", readiness.Diagnostic);
        Assert.Equal(1, fakeGatewayClient.CallCount);
    }

    [Fact]
    public async Task CheckReadinessAsync_MapsUnexpectedStatusFailureToRedactedError()
    {
        var fakeGatewayClient = new FakeGatewayClient
        {
            Exception = new InvalidOperationException("unexpected paper-user paper-password DU1234567 session=abc cookie=def failure"),
        };
        var service = CreateService(CreateReadyOptions(), fakeGatewayClient);

        var readiness = await service.CheckReadinessAsync();

        Assert.Equal(IbkrSessionReadinessStates.Error, readiness.State);
        Assert.Contains("[redacted]", readiness.Message);
        Assert.DoesNotContain("paper-user", readiness.Message);
        Assert.DoesNotContain("paper-password", readiness.Message);
        Assert.DoesNotContain("DU1234567", readiness.Message);
        Assert.DoesNotContain("abc", readiness.Message);
        Assert.DoesNotContain("def", readiness.Message);
        Assert.Equal(1, fakeGatewayClient.CallCount);
    }

    [Fact]
    public void FromReadiness_PreservesProviderNeutralBrokerStatusShape()
    {
        var options = CreateReadyOptions();
        var readiness = IbkrSessionReadinessResult.Create(
            options,
            IbkrSessionReadinessStates.Authenticated,
            "ready",
            authenticated: true,
            connected: true,
            competing: false);

        var status = IbkrBrokerStatus.FromReadiness(
            options,
            IbkrBrokerAdapterCapabilities.PaperSafeReadOnly,
            readiness);

        Assert.Equal(BrokerProviderStates.Authenticated, status.State);
        Assert.Equal("ibkr", status.Provider);
        Assert.Equal("paper", status.Mode);
        Assert.True(status.IntegrationEnabled);
        Assert.True(status.HasPaperAccountId);
        Assert.True(status.Authenticated);
        Assert.True(status.Connected);
        Assert.False(status.Competing);
        Assert.Equal("ready", status.Message);
        Assert.Equal(IbkrBrokerAdapterCapabilities.PaperSafeReadOnly, status.Capabilities);
    }

    private static IbkrSessionReadinessService CreateService(IbkrGatewayOptions options, FakeGatewayClient fakeGatewayClient)
    {
        var paperTradingGuard = new IbkrPaperTradingGuard(Options.Create(options));
        return new IbkrSessionReadinessService(
            options,
            paperTradingGuard,
            fakeGatewayClient,
            NullLogger<IbkrSessionReadinessService>.Instance);
    }

    private static IbkrGatewayOptions CreateReadyOptions() => new()
    {
        IntegrationEnabled = true,
        AccountMode = IbkrAccountMode.Paper,
        GatewayBaseUrl = new Uri("https://127.0.0.1:5000"),
        PaperAccountId = "DU1234567",
        Username = "paper-user",
        Password = "paper-password",
        GatewayContainer = new IbkrGatewayContainerOptions
        {
            Image = IbkrGatewayContainerOptions.DefaultIbeamImage,
            Port = 5000,
        },
    };

    private sealed class FakeGatewayClient : IIbkrGatewayClient
    {
        public int CallCount { get; private set; }

        public IbkrGatewaySessionStatus SessionStatus { get; set; } = new(
            Authenticated: false,
            Connected: false,
            Competing: false,
            Message: null,
            ServerName: null,
            ServerVersion: null);

        public Exception? Exception { get; set; }

        public Task<IbkrGatewaySessionStatus> GetSessionStatusAsync(CancellationToken cancellationToken = default)
        {
            CallCount++;

            if (Exception is not null)
            {
                throw Exception;
            }

            return Task.FromResult(SessionStatus);
        }
    }
}
