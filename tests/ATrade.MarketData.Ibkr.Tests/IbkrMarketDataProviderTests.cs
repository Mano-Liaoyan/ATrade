using System.Net;
using System.Net.Http.Json;
using ATrade.Brokers.Ibkr;
using ATrade.MarketData.Ibkr;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;

namespace ATrade.MarketData.Ibkr.Tests;

public sealed class IbkrMarketDataProviderTests
{
    [Fact]
    public void Provider_ReportsNotConfiguredWithoutConfiguredIbeamCredentialsAndDoesNotCallHttp()
    {
        var handler = new RecordingHttpMessageHandler((_, _) =>
            throw new InvalidOperationException("The fake handler must not receive requests when credentials are missing."));
        var options = CreateOptions(withCredentials: false);
        var provider = CreateProvider(handler, options);

        var status = provider.GetStatus();
        var result = provider.TryGetCandles("AAPL", MarketDataTimeframes.OneDay, out var candles, out var error);

        Assert.Equal(MarketDataProviderStates.NotConfigured, status.State);
        Assert.Equal(0, handler.CallCount);
        Assert.False(result);
        Assert.Null(candles);
        Assert.NotNull(error);
        Assert.Equal(MarketDataProviderErrorCodes.ProviderNotConfigured, error.Code);
        Assert.Contains("ignored local .env", error.Message);
    }

    [Fact]
    public void StreamingService_ReturnsProviderUnavailableWithoutFallbackSnapshot()
    {
        var handler = new RecordingHttpMessageHandler((_, _) =>
            throw new InvalidOperationException("The fake handler must not receive streaming snapshot requests when credentials are missing."));
        var provider = CreateProvider(handler, CreateOptions(withCredentials: false));
        var streamingService = new MarketDataStreamingService(provider, provider);

        var result = streamingService.TryCreateSnapshot("AAPL", MarketDataTimeframes.OneDay, out var update, out var error);

        Assert.False(result);
        Assert.Null(update);
        Assert.NotNull(error);
        Assert.Equal(MarketDataProviderErrorCodes.ProviderNotConfigured, error.Code);
        Assert.Equal(0, handler.CallCount);
    }

    [Fact]
    public void Provider_ReportsUnavailableWhenIbeamSessionIsNotAuthenticated()
    {
        var handler = new RecordingHttpMessageHandler((request, _) =>
        {
            Assert.Equal(HttpMethod.Get, request.Method);
            Assert.Equal(IbkrMarketDataClient.AuthStatusPath, request.RequestUri?.AbsolutePath);
            return Task.FromResult(JsonResponse(new
            {
                authenticated = false,
                connected = true,
                competing = false,
                message = "login required",
            }));
        });
        var provider = CreateProvider(handler, CreateOptions());

        var status = provider.GetStatus();

        Assert.Equal(MarketDataProviderStates.Unavailable, status.State);
        Assert.False(status.IsAvailable);
        Assert.Contains("not authenticated", status.Message);
        Assert.Equal(1, handler.CallCount);
    }

    [Fact]
    public void Provider_ReturnsProviderUnavailableWhenMarketDataEndpointRejectsUnauthenticatedSession()
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

            Assert.Equal(IbkrMarketDataClient.ContractSearchPath, request.RequestUri?.AbsolutePath);
            return Task.FromResult(new HttpResponseMessage(HttpStatusCode.Forbidden));
        });
        var provider = CreateProvider(handler, CreateOptions());

        var result = provider.TrySearchSymbols("AAPL", out var search, out var error);

        Assert.False(result);
        Assert.Null(search);
        Assert.NotNull(error);
        Assert.Equal(MarketDataProviderErrorCodes.AuthenticationRequired, error.Code);
        Assert.Contains("not authenticated", error.Message);
    }

    [Fact]
    public void Provider_MapsContractLookupSnapshotsHistoricalBarsAndScannerResults()
    {
        var handler = new RecordingHttpMessageHandler(RespondWithIbkrPayloads);
        var provider = CreateProvider(handler, CreateOptions());

        var status = provider.GetStatus();
        var trending = provider.GetTrendingSymbols();
        var searchResult = provider.TrySearchSymbols("AAPL", out var search, out var searchError);
        var symbolResult = provider.TryGetSymbol("AAPL", out var symbol);
        var candlesResult = provider.TryGetCandles("AAPL", MarketDataTimeframes.OneDay, out var candles, out var candlesError);
        var indicatorsResult = provider.TryGetIndicators("AAPL", MarketDataTimeframes.OneDay, out var indicators, out var indicatorsError);
        var latestResult = provider.TryGetLatestUpdate("AAPL", MarketDataTimeframes.OneDay, out var latest, out var latestError);

        Assert.True(status.IsAvailable);
        Assert.Equal(IbkrMarketDataSource.Scanner, trending.Source);
        var trendingSymbol = Assert.Single(trending.Symbols);
        Assert.Equal("AAPL", trendingSymbol.Symbol);
        Assert.Equal("Apple Inc.", trendingSymbol.Name);
        Assert.Equal(196.44m, trendingSymbol.LastPrice);
        Assert.Equal(1.18m, trendingSymbol.ChangePercent);
        Assert.Contains(trendingSymbol.Reasons, reason => reason.Contains("IBKR scanner", StringComparison.Ordinal));

        Assert.True(searchResult);
        Assert.Null(searchError);
        var searchMatch = Assert.Single(search!.Results);
        Assert.Equal(IbkrMarketDataSource.Provider, search!.Source);
        Assert.Equal("AAPL", searchMatch.Identity.Symbol);
        Assert.Equal(IbkrMarketDataSource.Provider, searchMatch.Identity.Provider);
        Assert.Equal("265598", searchMatch.Identity.ProviderSymbolId);
        Assert.Equal("Stock", searchMatch.Identity.AssetClass);
        Assert.Equal("NASDAQ", searchMatch.Identity.Exchange);
        Assert.Equal("USD", searchMatch.Identity.Currency);
        Assert.Equal("Apple Inc.", searchMatch.Name);

        Assert.True(symbolResult);
        Assert.NotNull(symbol);
        Assert.Equal("AAPL", symbol.Symbol);
        Assert.Equal(58_000_000, symbol.AverageVolume);

        Assert.True(candlesResult);
        Assert.Null(candlesError);
        Assert.Equal("AAPL", candles!.Symbol);
        Assert.Equal(MarketDataTimeframes.OneDay, candles.Timeframe);
        Assert.Equal(IbkrMarketDataSource.History, candles.Source);
        Assert.Equal(2, candles.Candles.Count);
        Assert.Equal(195.11m, candles.Candles[0].Open);
        Assert.Equal(58_000_000, candles.Candles[^1].Volume);

        Assert.True(indicatorsResult);
        Assert.Null(indicatorsError);
        Assert.Equal(IbkrMarketDataSource.History, indicators!.Source);
        Assert.Equal(2, indicators.MovingAverages.Count);
        Assert.Equal(2, indicators.Rsi.Count);
        Assert.Equal(2, indicators.Macd.Count);

        Assert.True(latestResult);
        Assert.Null(latestError);
        Assert.Equal("AAPL", latest!.Symbol);
        Assert.Equal(196.44m, latest.Close);
        Assert.Equal(58_000_000, latest.Volume);
        Assert.Equal(IbkrMarketDataSource.Snapshot, latest.Source);

        Assert.Contains(handler.Requests, request => request.Method == HttpMethod.Get && request.RequestUri!.AbsolutePath == IbkrMarketDataClient.ContractSearchPath);
        Assert.Contains(handler.Requests, request => request.Method == HttpMethod.Get && request.RequestUri!.AbsolutePath == IbkrMarketDataClient.ContractInfoPath);
        Assert.Contains(handler.Requests, request => request.Method == HttpMethod.Get && request.RequestUri!.AbsolutePath == IbkrMarketDataClient.SnapshotPath);
        Assert.Contains(handler.Requests, request => request.Method == HttpMethod.Get && request.RequestUri!.AbsolutePath == IbkrMarketDataClient.HistoricalDataPath);
        Assert.Contains(handler.Requests, request => request.Method == HttpMethod.Post && request.RequestUri!.AbsolutePath == IbkrMarketDataClient.ScannerPath);
    }

    private static IbkrGatewayOptions CreateOptions(bool withCredentials = true)
    {
        return new IbkrGatewayOptions
        {
            IntegrationEnabled = true,
            AccountMode = IbkrAccountMode.Paper,
            GatewayBaseUrl = new Uri("https://gateway.paper.local"),
            GatewayContainer =
            {
                Image = IbkrGatewayContainerOptions.DefaultIbeamImage,
                Port = 5000,
            },
            PaperAccountId = withCredentials ? "DU1234567" : IbkrGatewayPlaceholderValues.PaperAccountId,
            Username = withCredentials ? "paper-user" : IbkrGatewayPlaceholderValues.Username,
            Password = withCredentials ? "paper-password" : IbkrGatewayPlaceholderValues.Password,
        };
    }

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

    private static Task<HttpResponseMessage> RespondWithIbkrPayloads(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        Assert.False(cancellationToken.IsCancellationRequested);
        return Task.FromResult(request.RequestUri?.AbsolutePath switch
        {
            IbkrMarketDataClient.AuthStatusPath => JsonResponse(new
            {
                authenticated = true,
                connected = true,
                competing = false,
                message = "ready",
            }),
            IbkrMarketDataClient.ContractSearchPath => JsonResponse(new[]
            {
                new
                {
                    conid = "265598",
                    symbol = "AAPL",
                    companyName = "Apple Inc.",
                    secType = "STK",
                    sector = "Technology",
                },
            }),
            IbkrMarketDataClient.ContractInfoPath => JsonResponse(new[]
            {
                new
                {
                    conid = "265598",
                    symbol = "AAPL",
                    companyName = "Apple Inc.",
                    secType = "STK",
                    exchange = "NASDAQ",
                    currency = "USD",
                    sector = "Technology",
                },
            }),
            IbkrMarketDataClient.SnapshotPath => JsonResponse(new[]
            {
                new Dictionary<string, object?>
                {
                    ["conid"] = "265598",
                    ["55"] = "AAPL",
                    ["31"] = "196.44",
                    ["83"] = "1.18%",
                    ["7295"] = "195.00",
                    ["70"] = "198.10",
                    ["71"] = "194.75",
                    ["87"] = "58000000",
                },
            }),
            IbkrMarketDataClient.HistoricalDataPath => JsonResponse(new
            {
                data = new[]
                {
                    new { t = 1_714_521_600_000, o = 195.11m, h = 197.22m, l = 194.10m, c = 196.00m, v = 52_000_000 },
                    new { t = 1_714_608_000_000, o = 196.00m, h = 198.10m, l = 195.50m, c = 196.44m, v = 58_000_000 },
                },
            }),
            IbkrMarketDataClient.ScannerPath => JsonResponse(new[]
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
            }),
            _ => new HttpResponseMessage(HttpStatusCode.NotFound),
        });
    }

    private static HttpResponseMessage JsonResponse<T>(T payload) => new(HttpStatusCode.OK)
    {
        Content = JsonContent.Create(payload),
    };

    private sealed class RecordingHttpMessageHandler(
        Func<HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>> responder) : HttpMessageHandler
    {
        public List<HttpRequestMessage> Requests { get; } = [];

        public int CallCount => Requests.Count;

        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            Requests.Add(request);
            return responder(request, cancellationToken);
        }
    }
}
