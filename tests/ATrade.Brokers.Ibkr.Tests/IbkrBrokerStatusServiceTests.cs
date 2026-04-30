using ATrade.Brokers;
using Microsoft.Extensions.Logging.Abstractions;

namespace ATrade.Brokers.Ibkr.Tests;

public sealed class IbkrBrokerStatusServiceTests
{
    [Fact]
    public async Task GetStatusAsync_ReturnsDisabledWithoutCallingGateway()
    {
        var fakeGatewayClient = new FakeGatewayClient();
        var service = CreateService(
            new IbkrGatewayOptions
            {
                IntegrationEnabled = false,
                AccountMode = IbkrAccountMode.Paper,
            },
            fakeGatewayClient);

        var status = await service.GetStatusAsync();

        Assert.Equal("disabled", status.State);
        Assert.Equal("paper", status.Mode);
        Assert.Equal("ibkr", status.Provider);
        Assert.Equal(0, fakeGatewayClient.CallCount);
    }

    [Fact]
    public void Service_ExposesProviderNeutralIdentityAndCapabilities()
    {
        var service = CreateService(
            new IbkrGatewayOptions
            {
                IntegrationEnabled = false,
                AccountMode = IbkrAccountMode.Paper,
            },
            new FakeGatewayClient());

        Assert.IsAssignableFrom<IBrokerProvider>(service);
        Assert.Equal("ibkr", service.Identity.Provider);
        Assert.Equal("Interactive Brokers", service.Identity.DisplayName);
        Assert.True(service.Capabilities.SupportsSessionStatus);
        Assert.False(service.Capabilities.SupportsReadOnlyMarketData);
        Assert.False(service.Capabilities.SupportsBrokerOrderPlacement);
    }

    [Fact]
    public async Task GetStatusAsync_ReturnsRejectedLiveModeWithoutCallingGateway()
    {
        var fakeGatewayClient = new FakeGatewayClient();
        var service = CreateService(
            new IbkrGatewayOptions
            {
                IntegrationEnabled = true,
                AccountMode = IbkrAccountMode.Live,
                GatewayBaseUrl = new Uri("https://gateway.paper.local"),
            },
            fakeGatewayClient);

        var status = await service.GetStatusAsync();

        Assert.Equal("rejected-live-mode", status.State);
        Assert.Equal("live", status.Mode);
        Assert.Equal(0, fakeGatewayClient.CallCount);
    }

    [Fact]
    public async Task GetStatusAsync_ReturnsCredentialsMissingWithoutCallingGateway()
    {
        var fakeGatewayClient = new FakeGatewayClient();
        var service = CreateService(
            new IbkrGatewayOptions
            {
                IntegrationEnabled = true,
                AccountMode = IbkrAccountMode.Paper,
                GatewayBaseUrl = new Uri("https://gateway.paper.local"),
                PaperAccountId = IbkrGatewayPlaceholderValues.PaperAccountId,
                Username = IbkrGatewayPlaceholderValues.Username,
                Password = IbkrGatewayPlaceholderValues.Password,
                GatewayContainer = new IbkrGatewayContainerOptions
                {
                    Image = IbkrGatewayContainerOptions.DefaultIbeamImage,
                    Port = 5000,
                },
            },
            fakeGatewayClient);

        var status = await service.GetStatusAsync();

        Assert.Equal(BrokerProviderStates.CredentialsMissing, status.State);
        Assert.Equal("paper", status.Mode);
        Assert.False(status.HasPaperAccountId);
        Assert.Contains("ignored local .env", status.Message);
        Assert.DoesNotContain(IbkrGatewayPlaceholderValues.PaperAccountId, status.Message);
        Assert.Equal(0, fakeGatewayClient.CallCount);
    }

    [Fact]
    public async Task GetStatusAsync_ReturnsNotConfiguredWhenIbeamContainerContractIsMissing()
    {
        var fakeGatewayClient = new FakeGatewayClient();
        var service = CreateService(
            new IbkrGatewayOptions
            {
                IntegrationEnabled = true,
                AccountMode = IbkrAccountMode.Paper,
                GatewayBaseUrl = new Uri("https://gateway.paper.local"),
                PaperAccountId = "DU1234567",
                Username = "paper-user",
                Password = "paper-password",
                GatewayContainer = new IbkrGatewayContainerOptions
                {
                    Image = "example.invalid/ibkr-gateway-paper:local",
                    Port = 5000,
                },
            },
            fakeGatewayClient);

        var status = await service.GetStatusAsync();

        Assert.Equal(BrokerProviderStates.NotConfigured, status.State);
        Assert.Contains(IbkrGatewayContainerOptions.DefaultIbeamImage, status.Message);
        Assert.Equal(0, fakeGatewayClient.CallCount);
    }

    [Fact]
    public async Task GetStatusAsync_MapsConfiguredIbeamWhenEndpointIsNotReachableYet()
    {
        var fakeGatewayClient = new FakeGatewayClient
        {
            Exception = new HttpRequestException("connection refused for paper-user with paper-password"),
        };
        var service = CreateService(
            new IbkrGatewayOptions
            {
                IntegrationEnabled = true,
                AccountMode = IbkrAccountMode.Paper,
                GatewayBaseUrl = new Uri("https://gateway.paper.local"),
                PaperAccountId = "DU1234567",
                Username = "paper-user",
                Password = "paper-password",
                GatewayContainer = new IbkrGatewayContainerOptions
                {
                    Image = IbkrGatewayContainerOptions.DefaultIbeamImage,
                    Port = 5000,
                },
            },
            fakeGatewayClient);

        var status = await service.GetStatusAsync();

        Assert.Equal(BrokerProviderStates.IbeamContainerConfigured, status.State);
        Assert.Contains("waiting", status.Message);
        Assert.DoesNotContain("paper-user", status.Message);
        Assert.DoesNotContain("paper-password", status.Message);
        Assert.Equal(1, fakeGatewayClient.CallCount);
    }

    [Fact]
    public async Task GetStatusAsync_MapsAuthenticatedGatewaySessions()
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

        var service = CreateService(
            new IbkrGatewayOptions
            {
                IntegrationEnabled = true,
                AccountMode = IbkrAccountMode.Paper,
                GatewayBaseUrl = new Uri("https://gateway.paper.local"),
                PaperAccountId = "DU1234567",
                Username = "paper-user",
                Password = "paper-password",
                GatewayContainer = new IbkrGatewayContainerOptions
                {
                    Image = IbkrGatewayContainerOptions.DefaultIbeamImage,
                    Port = 5000,
                },
            },
            fakeGatewayClient);

        var status = await service.GetStatusAsync();

        Assert.Equal("authenticated", status.State);
        Assert.True(status.Authenticated);
        Assert.True(status.Connected);
        Assert.True(status.HasPaperAccountId);
        Assert.Equal(1, fakeGatewayClient.CallCount);
    }

    [Fact]
    public async Task GetStatusAsync_ReturnsRedactedErrorWhenGatewayStatusFailsUnexpectedly()
    {
        var fakeGatewayClient = new FakeGatewayClient
        {
            Exception = new InvalidOperationException("unexpected paper-user paper-password DU1234567 failure"),
        };

        var service = CreateService(
            new IbkrGatewayOptions
            {
                IntegrationEnabled = true,
                AccountMode = IbkrAccountMode.Paper,
                GatewayBaseUrl = new Uri("https://gateway.paper.local"),
                PaperAccountId = "DU1234567",
                Username = "paper-user",
                Password = "paper-password",
                GatewayContainer = new IbkrGatewayContainerOptions
                {
                    Image = IbkrGatewayContainerOptions.DefaultIbeamImage,
                    Port = 5000,
                },
            },
            fakeGatewayClient);

        var status = await service.GetStatusAsync();

        Assert.Equal(BrokerProviderStates.Error, status.State);
        Assert.Contains("[redacted]", status.Message);
        Assert.DoesNotContain("paper-user", status.Message);
        Assert.DoesNotContain("paper-password", status.Message);
        Assert.DoesNotContain("DU1234567", status.Message);
        Assert.Equal(1, fakeGatewayClient.CallCount);
    }

    private static IbkrBrokerStatusService CreateService(IbkrGatewayOptions options, FakeGatewayClient fakeGatewayClient)
    {
        var paperTradingGuard = new IbkrPaperTradingGuard(Microsoft.Extensions.Options.Options.Create(options));
        return new IbkrBrokerStatusService(
            options,
            paperTradingGuard,
            fakeGatewayClient,
            IbkrBrokerAdapterCapabilities.PaperSafeReadOnly,
            NullLogger<IbkrBrokerStatusService>.Instance);
    }

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
