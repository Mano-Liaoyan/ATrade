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
        Assert.Equal(0, fakeGatewayClient.CallCount);
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
    public async Task GetStatusAsync_ReturnsErrorWhenGatewayStatusFails()
    {
        var fakeGatewayClient = new FakeGatewayClient
        {
            Exception = new HttpRequestException("gateway unavailable"),
        };

        var service = CreateService(
            new IbkrGatewayOptions
            {
                IntegrationEnabled = true,
                AccountMode = IbkrAccountMode.Paper,
                GatewayBaseUrl = new Uri("https://gateway.paper.local"),
            },
            fakeGatewayClient);

        var status = await service.GetStatusAsync();

        Assert.Equal("error", status.State);
        Assert.Contains("gateway unavailable", status.Message);
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
