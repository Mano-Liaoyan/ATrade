using System.Net;
using System.Net.Http.Json;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Options;

namespace ATrade.Brokers.Ibkr.Tests;

public sealed class IbkrGatewayClientTests
{
    [Fact]
    public async Task GetSessionStatusAsync_UsesOfficialAuthStatusRouteAndParsesPayload()
    {
        var handler = new RecordingHttpMessageHandler((request, cancellationToken) =>
        {
            Assert.Equal(HttpMethod.Get, request.Method);
            Assert.Equal("https://gateway.paper.local/v1/api/iserver/auth/status", request.RequestUri?.ToString());
            Assert.False(cancellationToken.IsCancellationRequested);

            return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = JsonContent.Create(new
                {
                    authenticated = true,
                    connected = true,
                    competing = false,
                    message = "ready",
                    serverInfo = new
                    {
                        serverName = "paper-gateway",
                        serverVersion = "10.27.1",
                    },
                }),
            });
        });

        var gatewayClient = CreateGatewayClient(
            handler,
            new IbkrGatewayOptions
            {
                AccountMode = IbkrAccountMode.Paper,
                GatewayBaseUrl = new Uri("https://gateway.paper.local"),
            });

        var status = await gatewayClient.GetSessionStatusAsync();

        Assert.True(status.Authenticated);
        Assert.True(status.Connected);
        Assert.False(status.Competing);
        Assert.Equal("ready", status.Message);
        Assert.Equal("paper-gateway", status.ServerName);
        Assert.Equal("10.27.1", status.ServerVersion);
        Assert.Equal(1, handler.CallCount);
    }

    [Fact]
    public async Task GetSessionStatusAsync_RejectsLiveModeBeforeAnyHttpCall()
    {
        var handler = new RecordingHttpMessageHandler((_, _) =>
        {
            throw new InvalidOperationException("The fake handler must not receive requests for rejected live mode.");
        });

        var gatewayClient = CreateGatewayClient(
            handler,
            new IbkrGatewayOptions
            {
                AccountMode = IbkrAccountMode.Live,
                GatewayBaseUrl = new Uri("https://gateway.paper.local"),
            });

        var exception = await Assert.ThrowsAsync<IbkrPaperTradingRequiredException>(() => gatewayClient.GetSessionStatusAsync());

        Assert.Contains("Only Paper is supported", exception.Message);
        Assert.Equal(0, handler.CallCount);
    }

    [Fact]
    public void FromConfiguration_BindsTimeoutAndContainerMetadata()
    {
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(
                new Dictionary<string, string?>
                {
                    [IbkrGatewayEnvironmentVariables.IntegrationEnabled] = "true",
                    [IbkrGatewayEnvironmentVariables.AccountMode] = nameof(IbkrAccountMode.Paper),
                    [IbkrGatewayEnvironmentVariables.GatewayUrl] = "https://gateway.paper.local:5001",
                    [IbkrGatewayEnvironmentVariables.GatewayPort] = "5001",
                    [IbkrGatewayEnvironmentVariables.GatewayImage] = "registry.example/official-ibkr-gateway:latest",
                    [IbkrGatewayEnvironmentVariables.PaperAccountId] = "DU1234567",
                    [IbkrGatewayEnvironmentVariables.GatewayTimeoutSeconds] = "42",
                })
            .Build();

        var options = IbkrGatewayOptions.FromConfiguration(configuration);

        Assert.True(options.IntegrationEnabled);
        Assert.Equal(IbkrAccountMode.Paper, options.AccountMode);
        Assert.Equal(new Uri("https://gateway.paper.local:5001"), options.GatewayBaseUrl);
        Assert.Equal(TimeSpan.FromSeconds(42), options.RequestTimeout);
        Assert.Equal(5001, options.GatewayContainer.Port);
        Assert.Equal("registry.example/official-ibkr-gateway:latest", options.GatewayContainer.Image);
        Assert.Equal("DU1234567", options.PaperAccountId);
    }

    [Fact]
    public void PaperSafeCapabilities_StayReadOnlyAndOfficialOnly()
    {
        var capabilities = IbkrBrokerAdapterCapabilities.PaperSafeReadOnly;

        Assert.True(capabilities.SupportsSessionStatus);
        Assert.False(capabilities.SupportsBrokerOrderPlacement);
        Assert.False(capabilities.SupportsCredentialPersistence);
        Assert.False(capabilities.SupportsExecutionPersistence);
        Assert.True(capabilities.UsesOfficialApisOnly);
    }

    private static IbkrGatewayClient CreateGatewayClient(HttpMessageHandler handler, IbkrGatewayOptions options)
    {
        var httpClient = new HttpClient(handler)
        {
            BaseAddress = options.GatewayBaseUrl ?? new Uri("https://gateway.paper.local"),
            Timeout = options.RequestTimeout,
        };

        var paperTradingGuard = new IbkrPaperTradingGuard(Options.Create(options));
        return new IbkrGatewayClient(httpClient, paperTradingGuard);
    }

    private sealed class RecordingHttpMessageHandler(
        Func<HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>> responder) : HttpMessageHandler
    {
        public int CallCount { get; private set; }

        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            CallCount++;
            return responder(request, cancellationToken);
        }
    }
}
