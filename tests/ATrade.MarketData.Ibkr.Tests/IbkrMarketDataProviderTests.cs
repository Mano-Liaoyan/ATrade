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
    public async Task Provider_ReportsNotConfiguredWithoutConfiguredIbeamCredentialsAndDoesNotCallHttp()
    {
        var handler = new RecordingHttpMessageHandler((_, _) =>
            throw new InvalidOperationException("The fake handler must not receive requests when credentials are missing."));
        var options = CreateOptions(withCredentials: false);
        var provider = CreateProvider(handler, options);

        var status = await provider.GetStatusAsync(CancellationToken.None);
        var result = await provider.GetCandlesAsync("AAPL", MarketDataTimeframes.OneDay, cancellationToken: CancellationToken.None);

        Assert.Equal(MarketDataProviderStates.NotConfigured, status.State);
        Assert.Equal(0, handler.CallCount);
        Assert.True(result.IsFailure);
        Assert.Null(result.Value);
        Assert.NotNull(result.Error);
        Assert.Equal(MarketDataProviderErrorCodes.ProviderNotConfigured, result.Error!.Code);
        Assert.Contains("ignored local .env", result.Error.Message);
    }

    [Fact]
    public async Task StreamingService_ReturnsProviderUnavailableWithoutFallbackSnapshot()
    {
        var handler = new RecordingHttpMessageHandler((_, _) =>
            throw new InvalidOperationException("The fake handler must not receive streaming snapshot requests when credentials are missing."));
        var provider = CreateProvider(handler, CreateOptions(withCredentials: false));
        var streamingService = new MarketDataStreamingService(provider, provider);

        var result = await streamingService.CreateSnapshotAsync("AAPL", MarketDataTimeframes.OneDay, CancellationToken.None);

        Assert.True(result.IsFailure);
        Assert.Null(result.Value);
        Assert.NotNull(result.Error);
        Assert.Equal(MarketDataProviderErrorCodes.ProviderNotConfigured, result.Error!.Code);
        Assert.Equal(0, handler.CallCount);
    }

    [Fact]
    public async Task Provider_HonorsPreCanceledReadTokenBeforeGatewayRequest()
    {
        var handler = new RecordingHttpMessageHandler((_, _) =>
            throw new InvalidOperationException("The fake handler must not receive requests after cancellation."));
        var provider = CreateProvider(handler, CreateOptions());
        using var cancellation = new CancellationTokenSource();
        await cancellation.CancelAsync();

        await Assert.ThrowsAsync<OperationCanceledException>(() => provider.SearchSymbolsAsync("AAPL", cancellation.Token));

        Assert.Equal(0, handler.CallCount);
    }

    [Fact]
    public async Task Provider_ReportsUnavailableWhenIbeamSessionIsNotAuthenticated()
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

        var status = await provider.GetStatusAsync(CancellationToken.None);

        Assert.Equal(MarketDataProviderStates.Unavailable, status.State);
        Assert.False(status.IsAvailable);
        Assert.Contains("not authenticated", status.Message);
        Assert.Equal(1, handler.CallCount);
    }

    [Fact]
    public async Task Provider_ReportsSafeTransportDiagnosticWhenGatewayRequestFails()
    {
        var handler = new RecordingHttpMessageHandler((_, _) =>
            throw new HttpRequestException("connection reset by peer for paper-user through https://gateway.paper.local"));
        var provider = CreateProvider(handler, CreateOptions());

        var status = await provider.GetStatusAsync(CancellationToken.None);

        Assert.Equal(MarketDataProviderStates.Unavailable, status.State);
        Assert.Contains("local Client Portal HTTPS transport", status.Message);
        Assert.Contains("retry", status.Message);
        Assert.DoesNotContain("paper-user", status.Message);
        Assert.DoesNotContain("paper-password", status.Message);
        Assert.DoesNotContain("gateway.paper.local", status.Message);
        Assert.Equal(1, handler.CallCount);
    }

    [Fact]
    public async Task Provider_ReturnsProviderUnavailableWhenMarketDataEndpointRejectsUnauthenticatedSession()
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

        var result = await provider.SearchSymbolsAsync("AAPL", CancellationToken.None);

        Assert.True(result.IsFailure);
        Assert.Null(result.Value);
        Assert.NotNull(result.Error);
        Assert.Equal(MarketDataProviderErrorCodes.AuthenticationRequired, result.Error!.Code);
        Assert.Contains("not authenticated", result.Error.Message);
    }

    [Fact]
    public async Task Provider_ConvertsTrendingScannerEndpointFailureToSafeUnavailableError()
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
            return Task.FromResult(new HttpResponseMessage(HttpStatusCode.Forbidden));
        });
        var provider = CreateProvider(handler, CreateOptions());

        var result = await provider.GetTrendingSymbolsAsync(CancellationToken.None);

        Assert.True(result.IsFailure);
        Assert.Null(result.Value);
        Assert.NotNull(result.Error);
        Assert.Equal(MarketDataProviderErrorCodes.AuthenticationRequired, result.Error!.Code);
        Assert.Contains("not authenticated", result.Error.Message);
    }

    [Fact]
    public async Task Provider_CanonicalizesIbkrScannerSymbolsToExactIdentitySafeCodes()
    {
        var handler = new RecordingHttpMessageHandler((request, _) => Task.FromResult(request.RequestUri?.AbsolutePath switch
        {
            IbkrMarketDataClient.AuthStatusPath => JsonResponse(new
            {
                authenticated = true,
                connected = true,
                competing = false,
                message = "ready",
            }),
            IbkrMarketDataClient.ScannerPath => JsonResponse(new[]
            {
                new
                {
                    rank = 1,
                    conid = "54321",
                    symbol = "BRK B",
                    companyName = "Berkshire Hathaway Inc.",
                    secType = "STK",
                    exchange = "NYSE",
                    currency = "USD",
                    sector = "Financial Services",
                    score = 91.5m,
                    changePercent = 2.25m,
                    volume = 1_250_000,
                },
            }),
            IbkrMarketDataClient.SnapshotPath => JsonResponse(new[]
            {
                new Dictionary<string, object?>
                {
                    ["conid"] = "54321",
                    ["55"] = "BRK B",
                    ["31"] = "427.10",
                    ["83"] = "2.25%",
                    ["87"] = "1250000",
                },
            }),
            _ => new HttpResponseMessage(HttpStatusCode.NotFound),
        }));
        var provider = CreateProvider(handler, CreateOptions());

        var result = await provider.GetTrendingSymbolsAsync(CancellationToken.None);

        Assert.True(result.IsSuccess);
        Assert.Null(result.Error);
        var trendingSymbol = Assert.Single(result.Value!.Symbols);
        Assert.Equal("BRK.B", trendingSymbol.Symbol);
        Assert.Equal("BRK.B", trendingSymbol.Identity?.Symbol);
        Assert.Equal("54321", trendingSymbol.Identity?.ProviderSymbolId);
        Assert.Equal("NYSE", trendingSymbol.Identity?.Exchange);
        Assert.Equal("USD", trendingSymbol.Identity?.Currency);
    }

    [Fact]
    public async Task Provider_UsesSearchContractWhenStockDetailEndpointRequiresMonth()
    {
        var handler = new RecordingHttpMessageHandler((request, _) =>
        {
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
                        conid = "4815747",
                        companyHeader = "NVIDIA CORP (NASDAQ)",
                        symbol = "NVDA",
                        secType = "STK",
                        sections = Array.Empty<object>(),
                    },
                }),
                IbkrMarketDataClient.ContractInfoPath => new HttpResponseMessage(HttpStatusCode.BadRequest)
                {
                    Content = JsonContent.Create(new
                    {
                        error = "Bad Request: month required",
                        statusCode = 400,
                    }),
                },
                _ => new HttpResponseMessage(HttpStatusCode.NotFound),
            });
        });
        var provider = CreateProvider(handler, CreateOptions());

        var result = await provider.SearchSymbolsAsync("NVDA", CancellationToken.None);
        var search = result.Value;

        Assert.True(result.IsSuccess);
        Assert.Null(result.Error);
        var match = Assert.Single(search!.Results);
        Assert.Equal("NVDA", match.Identity.Symbol);
        Assert.Equal("4815747", match.Identity.ProviderSymbolId);
        Assert.Equal("NVIDIA CORP", match.Name);
        Assert.Equal("NASDAQ", match.Identity.Exchange);
        Assert.Contains(handler.Requests, request => request.RequestUri!.AbsolutePath == IbkrMarketDataClient.ContractInfoPath);
    }

    [Fact]
    public async Task Provider_MapsContractLookupSnapshotsHistoricalBarsAndScannerResults()
    {
        var handler = new RecordingHttpMessageHandler(RespondWithIbkrPayloads);
        var provider = CreateProvider(handler, CreateOptions());

        var status = await provider.GetStatusAsync(CancellationToken.None);
        var trendingResult = await provider.GetTrendingSymbolsAsync(CancellationToken.None);
        var trending = trendingResult.Value;
        var searchResult = await provider.SearchSymbolsAsync("AAPL", CancellationToken.None);
        var search = searchResult.Value;
        var symbolResult = await provider.GetSymbolAsync("AAPL", CancellationToken.None);
        var symbol = symbolResult.Value;
        var candlesResult = await provider.GetCandlesAsync("AAPL", MarketDataTimeframes.OneDay, cancellationToken: CancellationToken.None);
        var candles = candlesResult.Value;
        var indicatorsResult = await provider.GetIndicatorsAsync("AAPL", MarketDataTimeframes.OneDay, cancellationToken: CancellationToken.None);
        var indicators = indicatorsResult.Value;
        var latestResult = await provider.GetLatestUpdateAsync("AAPL", MarketDataTimeframes.OneDay, cancellationToken: CancellationToken.None);
        var latest = latestResult.Value;

        Assert.True(status.IsAvailable);
        Assert.True(trendingResult.IsSuccess);
        Assert.NotNull(trending);
        Assert.Equal(IbkrMarketDataSource.Scanner, trending!.Source);
        var trendingSymbol = Assert.Single(trending.Symbols);
        Assert.Equal("AAPL", trendingSymbol.Symbol);
        Assert.Equal("Apple Inc.", trendingSymbol.Name);
        Assert.Equal(196.44m, trendingSymbol.LastPrice);
        Assert.Equal(1.18m, trendingSymbol.ChangePercent);
        Assert.Contains(trendingSymbol.Reasons, reason => reason.Contains("IBKR scanner", StringComparison.Ordinal));

        Assert.True(searchResult.IsSuccess);
        Assert.Null(searchResult.Error);
        var searchMatch = Assert.Single(search!.Results);
        Assert.Equal(IbkrMarketDataSource.Provider, search!.Source);
        Assert.Equal("AAPL", searchMatch.Identity.Symbol);
        Assert.Equal(IbkrMarketDataSource.Provider, searchMatch.Identity.Provider);
        Assert.Equal("265598", searchMatch.Identity.ProviderSymbolId);
        Assert.Equal(MarketDataAssetClasses.Stock, searchMatch.Identity.AssetClass);
        Assert.Equal("NASDAQ", searchMatch.Identity.Exchange);
        Assert.Equal("USD", searchMatch.Identity.Currency);
        Assert.Equal("Apple Inc.", searchMatch.Name);

        Assert.True(symbolResult.IsSuccess);
        Assert.NotNull(symbol);
        Assert.Equal("AAPL", symbol.Symbol);
        Assert.Equal(58_000_000, symbol.AverageVolume);

        Assert.True(candlesResult.IsSuccess);
        Assert.Null(candlesResult.Error);
        Assert.Equal("AAPL", candles!.Symbol);
        Assert.Equal(MarketDataTimeframes.OneDay, candles.Timeframe);
        Assert.Equal(IbkrMarketDataSource.History, candles.Source);
        Assert.Equal(2, candles.Candles.Count);
        Assert.Equal(195.11m, candles.Candles[0].Open);
        Assert.Equal(58_000_000, candles.Candles[^1].Volume);

        Assert.True(indicatorsResult.IsSuccess);
        Assert.Null(indicatorsResult.Error);
        Assert.Equal(IbkrMarketDataSource.History, indicators!.Source);
        Assert.Equal(2, indicators.MovingAverages.Count);
        Assert.Equal(2, indicators.Rsi.Count);
        Assert.Equal(2, indicators.Macd.Count);

        Assert.True(latestResult.IsSuccess);
        Assert.Null(latestResult.Error);
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

    [Theory]
    [InlineData(ChartRangePresets.OneMinute, "1d", "1min")]
    [InlineData(ChartRangePresets.FiveMinutes, "1d", "1min")]
    [InlineData(ChartRangePresets.OneHour, "1d", "1min")]
    [InlineData(ChartRangePresets.SixHours, "1d", "5min")]
    [InlineData(ChartRangePresets.OneDay, "2d", "5min")]
    [InlineData(ChartRangePresets.OneMonth, "1m", "1d")]
    [InlineData(ChartRangePresets.SixMonths, "6m", "1d")]
    [InlineData(ChartRangePresets.OneYear, "1y", "1d")]
    [InlineData(ChartRangePresets.FiveYears, "5y", "1w")]
    [InlineData(ChartRangePresets.All, "10y", "1w")]
    public async Task Provider_MapsSupportedChartRangesToIbkrHistoricalRequestHints(string chartRange, string expectedPeriod, string expectedBar)
    {
        var handler = new RecordingHttpMessageHandler((request, cancellationToken) =>
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
                    new { conid = "265598", symbol = "AAPL", companyName = "Apple Inc.", secType = "STK", sector = "Technology" },
                }),
                IbkrMarketDataClient.ContractInfoPath => JsonResponse(new[]
                {
                    new { conid = "265598", symbol = "AAPL", companyName = "Apple Inc.", secType = "STK", exchange = "NASDAQ", currency = "USD", sector = "Technology" },
                }),
                IbkrMarketDataClient.HistoricalDataPath => HistoricalResponseForRequest(request, expectedPeriod, expectedBar),
                _ => new HttpResponseMessage(HttpStatusCode.NotFound),
            });
        });
        var provider = CreateProvider(handler, CreateOptions());

        var result = await provider.GetCandlesAsync("AAPL", chartRange, cancellationToken: CancellationToken.None);

        Assert.True(result.IsSuccess);
        Assert.Null(result.Error);
        Assert.Equal(chartRange, result.Value!.Timeframe);
        Assert.Contains(handler.Requests, request => request.RequestUri!.AbsolutePath == IbkrMarketDataClient.HistoricalDataPath);
    }

    [Fact]
    public async Task Provider_FiltersHistoricalBarsToRequestedLookbackWindow()
    {
        var recentTime = DateTimeOffset.UtcNow.AddHours(-2);
        var staleTime = DateTimeOffset.UtcNow.AddDays(-2);
        var handler = new RecordingHttpMessageHandler((request, cancellationToken) =>
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
                    new { conid = "265598", symbol = "AAPL", companyName = "Apple Inc.", secType = "STK", sector = "Technology" },
                }),
                IbkrMarketDataClient.ContractInfoPath => JsonResponse(new[]
                {
                    new { conid = "265598", symbol = "AAPL", companyName = "Apple Inc.", secType = "STK", exchange = "NASDAQ", currency = "USD", sector = "Technology" },
                }),
                IbkrMarketDataClient.HistoricalDataPath => JsonResponse(new
                {
                    data = new[]
                    {
                        new { t = ToUnixMilliseconds(staleTime), o = 190.00m, h = 191.00m, l = 189.00m, c = 190.50m, v = 1000 },
                        new { t = ToUnixMilliseconds(recentTime), o = 195.11m, h = 197.22m, l = 194.10m, c = 196.00m, v = 52_000_000 },
                    },
                }),
                _ => new HttpResponseMessage(HttpStatusCode.NotFound),
            });
        });
        var provider = CreateProvider(handler, CreateOptions());

        var result = await provider.GetCandlesAsync("AAPL", ChartRangePresets.OneDay, cancellationToken: CancellationToken.None);

        Assert.True(result.IsSuccess);
        var candle = Assert.Single(result.Value!.Candles);
        Assert.Equal(195.11m, candle.Open);
        Assert.Equal(52_000_000, candle.Volume);
    }

    [Fact]
    public async Task Provider_ReturnsSupportedChartRangeErrorForUnsupportedHistoricalRange()
    {
        var handler = new RecordingHttpMessageHandler((request, _) => Task.FromResult(request.RequestUri?.AbsolutePath switch
        {
            IbkrMarketDataClient.AuthStatusPath => JsonResponse(new
            {
                authenticated = true,
                connected = true,
                competing = false,
                message = "ready",
            }),
            _ => new HttpResponseMessage(HttpStatusCode.NotFound),
        }));
        var provider = CreateProvider(handler, CreateOptions());

        var result = await provider.GetCandlesAsync("AAPL", "5m", cancellationToken: CancellationToken.None);

        Assert.True(result.IsFailure);
        Assert.Equal(MarketDataProviderErrorCodes.UnsupportedChartRange, result.Error?.Code);
        Assert.Contains("Supported values: 1min, 5mins", result.Error?.Message);
        Assert.DoesNotContain(handler.Requests, request => request.RequestUri!.AbsolutePath == IbkrMarketDataClient.HistoricalDataPath);
    }

    private static IbkrGatewayOptions CreateOptions(bool withCredentials = true)
    {
        return new IbkrGatewayOptions
        {
            IntegrationEnabled = true,
            AccountMode = IbkrAccountMode.Paper,
            GatewayBaseUrl = new Uri("https://127.0.0.1:5000"),
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
        var gatewayHttpClient = new HttpClient(handler)
        {
            BaseAddress = options.GatewayBaseUrl,
            Timeout = options.RequestTimeout,
        };
        var marketDataHttpClient = new HttpClient(handler)
        {
            BaseAddress = options.GatewayBaseUrl,
            Timeout = options.RequestTimeout,
        };
        var paperTradingGuard = new IbkrPaperTradingGuard(Options.Create(options));
        var readinessService = new IbkrSessionReadinessService(
            options,
            paperTradingGuard,
            new IbkrGatewayClient(gatewayHttpClient, paperTradingGuard),
            NullLogger<IbkrSessionReadinessService>.Instance);
        var client = new IbkrMarketDataClient(marketDataHttpClient);
        return new IbkrMarketDataProvider(
            options,
            readinessService,
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
                data = CreateRecentHistoricalPayloadBars(),
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

    private static HttpResponseMessage HistoricalResponseForRequest(HttpRequestMessage request, string expectedPeriod, string expectedBar)
    {
        Assert.Contains($"period={Uri.EscapeDataString(expectedPeriod)}", request.RequestUri!.Query, StringComparison.Ordinal);
        Assert.Contains($"bar={Uri.EscapeDataString(expectedBar)}", request.RequestUri!.Query, StringComparison.Ordinal);
        return JsonResponse(new
        {
            data = CreateRecentHistoricalPayloadBars(),
        });
    }

    private static object[] CreateRecentHistoricalPayloadBars() =>
    [
        new { t = ToUnixMilliseconds(DateTimeOffset.UtcNow.AddSeconds(-30)), o = 195.11m, h = 197.22m, l = 194.10m, c = 196.00m, v = 52_000_000 },
        new { t = ToUnixMilliseconds(DateTimeOffset.UtcNow.AddSeconds(-10)), o = 196.00m, h = 198.10m, l = 195.50m, c = 196.44m, v = 58_000_000 },
    ];

    private static long ToUnixMilliseconds(DateTimeOffset time) => time.ToUnixTimeMilliseconds();

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
