using System.Net;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using ATrade.Brokers.Ibkr;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;

namespace ATrade.MarketData.Ibkr.Tests;

public sealed class IbkrScannerRequestContractTests
{
    [Fact]
    public async Task GetTrendingScannerResultsAsync_SendsBufferedJsonWithContentLengthAndNoChunkedTransfer()
    {
        var handler = new RecordingHttpMessageHandler(async (request, cancellationToken) =>
        {
            Assert.Equal(HttpMethod.Post, request.Method);
            Assert.Equal(IbkrMarketDataClient.ScannerPath, request.RequestUri?.AbsolutePath);
            Assert.NotNull(request.Content);
            Assert.Equal("application/json", request.Content.Headers.ContentType?.MediaType);
            Assert.True(request.Content.Headers.ContentLength > 0);
            Assert.NotEqual(true, request.Headers.TransferEncodingChunked);

            var body = await request.Content.ReadAsStringAsync(cancellationToken);
            Assert.Equal(request.Content.Headers.ContentLength, Encoding.UTF8.GetByteCount(body));

            using var document = JsonDocument.Parse(body);
            var root = document.RootElement;
            Assert.Equal("STK", root.GetProperty("instrument").GetString());
            Assert.Equal("STK.US.MAJOR", root.GetProperty("location").GetString());
            Assert.Equal("TOP_PERC_GAIN", root.GetProperty("type").GetString());
            Assert.Equal(JsonValueKind.Array, root.GetProperty("filter").ValueKind);
            Assert.Equal(0, root.GetProperty("filter").GetArrayLength());

            return JsonResponse(new[]
            {
                new
                {
                    rank = 1,
                    conid = "265598",
                    symbol = "AAPL",
                    companyName = "Apple Inc.",
                    secType = "STK",
                    exchange = "NASDAQ",
                    currency = "USD",
                    sector = "Technology",
                    score = 99.4m,
                    changePercent = 1.18m,
                    volume = 58_000_000,
                },
            });
        });
        var client = CreateClient(handler);

        var results = await client.GetTrendingScannerResultsAsync();

        var result = Assert.Single(results);
        Assert.Equal("AAPL", result.Symbol);
        Assert.Equal("265598", result.Conid);
        Assert.Equal(IbkrMarketDataSource.Scanner, result.Source);
        Assert.Equal(1, handler.CallCount);
    }

    [Fact]
    public async Task Provider_ConvertsScannerLengthRequiredToSafeUnavailableErrorWithoutLeakingConfiguredSecrets()
    {
        var handler = new RecordingHttpMessageHandler((request, _) =>
        {
            if (request.RequestUri?.AbsolutePath == IbkrMarketDataClient.AuthStatusPath)
            {
                return Task.FromResult(JsonResponse(new
                {
                    authenticated = true,
                    connected = true,
                    competing = false,
                    message = "ready",
                }));
            }

            Assert.Equal(HttpMethod.Post, request.Method);
            Assert.Equal(IbkrMarketDataClient.ScannerPath, request.RequestUri?.AbsolutePath);
            return Task.FromResult(new HttpResponseMessage(HttpStatusCode.LengthRequired)
            {
                ReasonPhrase = "Length Required",
                Content = new StringContent(
                    "<html>Length required for paper-user; password=paper-password; account DU1234567; token=abc123; Set-Cookie: SESSION=secret; https://127.0.0.1:5000</html>",
                    Encoding.UTF8,
                    "text/html"),
            });
        });
        var provider = CreateProvider(handler, CreateOptions());

        var result = await provider.GetTrendingSymbolsAsync(CancellationToken.None);

        Assert.True(result.IsFailure);
        Assert.Null(result.Value);
        Assert.NotNull(result.Error);
        Assert.Equal(MarketDataProviderErrorCodes.ProviderUnavailable, result.Error!.Code);
        Assert.Contains("411", result.Error.Message);
        Assert.Contains("Length Required", result.Error.Message);
        Assert.DoesNotContain("paper-user", result.Error.Message, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("paper-password", result.Error.Message, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("DU1234567", result.Error.Message, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("abc123", result.Error.Message, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("SESSION=secret", result.Error.Message, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("127.0.0.1", result.Error.Message, StringComparison.OrdinalIgnoreCase);
    }

    private static IbkrMarketDataClient CreateClient(HttpMessageHandler handler) => new(new HttpClient(handler)
    {
        BaseAddress = new Uri("https://127.0.0.1:5000"),
    });

    private static IbkrMarketDataProvider CreateProvider(HttpMessageHandler handler, IbkrGatewayOptions options)
    {
        var httpClient = new HttpClient(handler)
        {
            BaseAddress = options.GatewayBaseUrl,
            Timeout = options.RequestTimeout,
        };
        var client = new IbkrMarketDataClient(httpClient);
        return new IbkrMarketDataProvider(
            options,
            new IbkrPaperTradingGuard(Options.Create(options)),
            client,
            new IndicatorService(),
            NullLogger<IbkrMarketDataProvider>.Instance);
    }

    private static IbkrGatewayOptions CreateOptions() => new()
    {
        IntegrationEnabled = true,
        AccountMode = IbkrAccountMode.Paper,
        GatewayBaseUrl = new Uri("https://127.0.0.1:5000"),
        GatewayContainer =
        {
            Image = IbkrGatewayContainerOptions.DefaultIbeamImage,
            Port = 5000,
        },
        PaperAccountId = "DU1234567",
        Username = "paper-user",
        Password = "paper-password",
    };

    private static HttpResponseMessage JsonResponse<T>(T payload) => new(HttpStatusCode.OK)
    {
        Content = JsonContent.Create(payload),
    };

    private sealed class RecordingHttpMessageHandler(
        Func<HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>> responder) : HttpMessageHandler
    {
        public int CallCount { get; private set; }

        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            CallCount++;
            return await responder(request, cancellationToken).ConfigureAwait(false);
        }
    }
}
