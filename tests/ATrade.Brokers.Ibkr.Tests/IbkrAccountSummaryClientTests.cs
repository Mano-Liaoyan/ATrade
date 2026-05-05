using System.Net;
using System.Net.Http.Json;
using Microsoft.Extensions.Options;

namespace ATrade.Brokers.Ibkr.Tests;

public sealed class IbkrAccountSummaryClientTests
{
    private const string ConfiguredPaperAccountId = "PAPER_TEST_ACCOUNT";

    [Fact]
    public async Task GetConfiguredPaperAccountBalanceAsync_UsesClientPortalPortfolioSummaryRouteAndParsesTotalCashValue()
    {
        var handler = new RecordingHttpMessageHandler((request, cancellationToken) =>
        {
            Assert.Equal(HttpMethod.Get, request.Method);
            Assert.Equal(
                "https://gateway.paper.local/v1/api/portfolio/PAPER_TEST_ACCOUNT/summary",
                request.RequestUri?.ToString());
            Assert.False(cancellationToken.IsCancellationRequested);

            return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = JsonContent.Create(new
                {
                    totalcashvalue = new
                    {
                        amount = "12345.67",
                        currency = "usd",
                    },
                    netliquidation = new
                    {
                        amount = "99999.99",
                        currency = "USD",
                    },
                }),
            });
        });
        var client = CreateClient(handler, CreateReadyOptions());

        var balance = await client.GetConfiguredPaperAccountBalanceAsync();

        Assert.Equal(12345.67m, balance.Amount);
        Assert.Equal("USD", balance.Currency);
        Assert.Equal("totalcashvalue", balance.Metric);
        Assert.Equal(1, handler.CallCount);
    }

    [Fact]
    public async Task GetConfiguredPaperAccountBalanceAsync_FallsBackToNetLiquidationWhenCashValueIsMissing()
    {
        var handler = new RecordingHttpMessageHandler((_, _) => Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = JsonContent.Create(new
            {
                netLiquidation = new
                {
                    value = 54321.01m,
                    currency = "USD",
                },
            }),
        }));
        var client = CreateClient(handler, CreateReadyOptions());

        var balance = await client.GetConfiguredPaperAccountBalanceAsync();

        Assert.Equal(54321.01m, balance.Amount);
        Assert.Equal("USD", balance.Currency);
        Assert.Equal("netliquidation", balance.Metric);
    }

    [Fact]
    public async Task GetConfiguredPaperAccountBalanceAsync_RejectsLiveModeBeforeHttpCall()
    {
        var options = CreateReadyOptions();
        options.AccountMode = IbkrAccountMode.Live;
        var handler = new RecordingHttpMessageHandler((_, _) => throw new InvalidOperationException("No HTTP call expected."));
        var client = CreateClient(handler, options);

        await Assert.ThrowsAsync<IbkrPaperTradingRequiredException>(() => client.GetConfiguredPaperAccountBalanceAsync());
        Assert.Equal(0, handler.CallCount);
    }

    private static IbkrAccountSummaryClient CreateClient(HttpMessageHandler handler, IbkrGatewayOptions options)
    {
        var httpClient = new HttpClient(handler)
        {
            BaseAddress = options.GatewayBaseUrl,
            Timeout = options.RequestTimeout,
        };
        var paperTradingGuard = new IbkrPaperTradingGuard(Options.Create(options));
        return new IbkrAccountSummaryClient(httpClient, options, paperTradingGuard);
    }

    private static IbkrGatewayOptions CreateReadyOptions() => new()
    {
        IntegrationEnabled = true,
        AccountMode = IbkrAccountMode.Paper,
        GatewayBaseUrl = new Uri("https://gateway.paper.local"),
        PaperAccountId = ConfiguredPaperAccountId,
        Username = "paper-user",
        Password = "paper-password",
        GatewayContainer = new IbkrGatewayContainerOptions
        {
            Image = IbkrGatewayContainerOptions.DefaultIbeamImage,
            Port = 5000,
        },
    };

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
