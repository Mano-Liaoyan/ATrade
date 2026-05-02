using ATrade.Accounts;
using ATrade.Analysis;
using ATrade.Analysis.Lean;
using ATrade.Brokers;
using ATrade.Brokers.Ibkr;
using ATrade.MarketData;
using ATrade.MarketData.Ibkr;
using ATrade.MarketData.Timescale;
using ATrade.Orders;
using ATrade.ServiceDefaults;
using ATrade.Workspaces;

var builder = WebApplication.CreateBuilder(args);

LocalDevelopmentPortContractLoader.ApplyApiHttpPortDefault(builder);
builder.AddServiceDefaults();
builder.Services.AddIbkrBrokerAdapter(builder.Configuration);
builder.Services.AddAccountsModule();
builder.Services.AddOrdersModule();
builder.Services.AddMarketDataModule();
builder.Services.AddTimescaleMarketDataPersistence(builder.Configuration);
builder.Services.AddAnalysisModule();
builder.Services.AddLeanAnalysisEngine(builder.Configuration);
builder.Services.AddIbkrMarketDataProvider();
builder.Services.AddTimescaleMarketDataCacheAside();
builder.Services.AddWorkspacesModule(builder.Configuration);
builder.Services.AddSignalR();
builder.Services.AddCors(options =>
{
    options.AddPolicy("LocalFrontend", policy =>
        policy
            .SetIsOriginAllowed(origin =>
                Uri.TryCreate(origin, UriKind.Absolute, out var uri)
                && (string.Equals(uri.Host, "localhost", StringComparison.OrdinalIgnoreCase) || string.Equals(uri.Host, "127.0.0.1", StringComparison.OrdinalIgnoreCase)))
            .AllowAnyHeader()
            .AllowAnyMethod()
            .AllowCredentials());
});

var app = builder.Build();

app.UseCors("LocalFrontend");

app.MapGet("/health", () => Results.Text("ok", "text/plain"));
app.MapGet("/api/accounts/overview", (IAccountOverviewProvider overviewProvider) => Results.Ok(overviewProvider.GetOverview()));
app.MapGet(
    "/api/market-data/trending",
    async (IMarketDataService marketDataService, CancellationToken cancellationToken) =>
        ToMarketDataResult(await marketDataService.GetTrendingSymbolsAsync(cancellationToken)));
app.MapGet(
    "/api/market-data/search",
    async (string? query, string? assetClass, int? limit, IMarketDataService marketDataService, CancellationToken cancellationToken) =>
        ToMarketDataResult(await marketDataService.SearchSymbolsAsync(query, assetClass, limit, cancellationToken)));
app.MapGet(
    "/api/market-data/{symbol}/candles",
    async (string symbol, string? timeframe, string? provider, string? providerSymbolId, string? exchange, string? currency, string? assetClass, IMarketDataService marketDataService, CancellationToken cancellationToken) =>
    {
        var identity = CreateOptionalSymbolIdentity(symbol, provider, providerSymbolId, exchange, currency, assetClass);
        return ToMarketDataResult(await marketDataService.GetCandlesAsync(symbol, timeframe, identity, cancellationToken));
    });
app.MapGet(
    "/api/market-data/{symbol}/indicators",
    async (string symbol, string? timeframe, string? provider, string? providerSymbolId, string? exchange, string? currency, string? assetClass, IMarketDataService marketDataService, CancellationToken cancellationToken) =>
    {
        var identity = CreateOptionalSymbolIdentity(symbol, provider, providerSymbolId, exchange, currency, assetClass);
        return ToMarketDataResult(await marketDataService.GetIndicatorsAsync(symbol, timeframe, identity, cancellationToken));
    });
app.MapGet(
    "/api/analysis/engines",
    (IAnalysisEngineRegistry analysisEngines) => Results.Ok(analysisEngines.GetEngines()));
app.MapPost(
    "/api/analysis/run",
    async (AnalysisRunApiRequest request, IAnalysisEngineRegistry analysisEngines, IMarketDataService marketDataService, CancellationToken cancellationToken) =>
    {
        var analysisRequestResult = await CreateAnalysisRequestAsync(request, marketDataService, cancellationToken);
        if (analysisRequestResult.ErrorResult is not null)
        {
            return analysisRequestResult.ErrorResult;
        }

        cancellationToken.ThrowIfCancellationRequested();
        var result = await analysisEngines.AnalyzeAsync(analysisRequestResult.Request!, cancellationToken);
        return ToAnalysisResult(result);
    });
app.MapGet(
    "/api/broker/ibkr/status",
    async (IBrokerProvider brokerProvider, CancellationToken cancellationToken) =>
        Results.Ok(await brokerProvider.GetStatusAsync(cancellationToken)));
app.MapPost(
    "/api/orders/simulate",
    (OrderSimulationRequest request, IOrderSimulationService simulationService) =>
    {
        try
        {
            return Results.Ok(simulationService.Simulate(request));
        }
        catch (OrderSimulationValidationException exception)
        {
            return Results.BadRequest(new
            {
                simulated = false,
                error = exception.Message,
            });
        }
        catch (IbkrPaperTradingRequiredException exception)
        {
            return Results.Conflict(new
            {
                simulated = false,
                error = exception.Message,
            });
        }
    });

app.MapGet("/api/workspace/watchlist", GetWorkspaceWatchlistAsync);
app.MapPut("/api/workspace/watchlist", ReplaceWorkspaceWatchlistAsync);
app.MapPost("/api/workspace/watchlist", PinWorkspaceWatchlistSymbolAsync);
app.MapDelete("/api/workspace/watchlist/pins/{instrumentKey}", UnpinWorkspaceWatchlistInstrumentAsync);
app.MapDelete("/api/workspace/watchlist/{symbol}", UnpinWorkspaceWatchlistSymbolAsync);

app.MapHub<MarketDataHub>("/hubs/market-data");

app.Run();

static IResult ToMarketDataResult<T>(MarketDataReadResult<T> result) where T : class =>
    result.IsSuccess && result.Value is not null
        ? Results.Ok(result.Value)
        : ToMarketDataErrorResult(result.Error);

static IResult ToMarketDataErrorResult(MarketDataError? error)
{
    if (error is null)
    {
        return Results.BadRequest(new MarketDataError(MarketDataProviderErrorCodes.MarketDataRequestFailed, "Market-data request failed."));
    }

    return error.Code switch
    {
        MarketDataProviderErrorCodes.UnsupportedSymbol => Results.NotFound(error),
        MarketDataProviderErrorCodes.ProviderNotConfigured or MarketDataProviderErrorCodes.ProviderUnavailable or MarketDataProviderErrorCodes.AuthenticationRequired => Results.Json(
            error,
            statusCode: StatusCodes.Status503ServiceUnavailable),
        _ => Results.BadRequest(error),
    };
}

static IResult ToAnalysisResult(AnalysisResult result) => result.Error?.Code switch
{
    AnalysisEngineErrorCodes.EngineNotConfigured or AnalysisEngineErrorCodes.EngineUnavailable => Results.Json(
        result,
        statusCode: StatusCodes.Status503ServiceUnavailable),
    AnalysisEngineErrorCodes.InvalidRequest => Results.BadRequest(result),
    _ => string.Equals(result.Status, AnalysisResultStatuses.Failed, StringComparison.OrdinalIgnoreCase)
        ? Results.BadRequest(result)
        : Results.Ok(result),
};

static async Task<AnalysisRequestBuildResult> CreateAnalysisRequestAsync(
    AnalysisRunApiRequest? request,
    IMarketDataService marketDataService,
    CancellationToken cancellationToken)
{
    cancellationToken.ThrowIfCancellationRequested();
    if (request is null)
    {
        return AnalysisRequestBuildResult.Failure(Results.BadRequest(new AnalysisError(AnalysisEngineErrorCodes.InvalidRequest, "An analysis request payload is required.")));
    }

    var timeframe = string.IsNullOrWhiteSpace(request.Timeframe) ? MarketDataTimeframes.OneDay : request.Timeframe.Trim();
    var symbol = request.Symbol ?? CreateSymbolIdentityFromCode(request.SymbolCode);
    var bars = request.Bars;

    if (bars is null || bars.Count == 0)
    {
        var symbolCode = symbol?.Symbol ?? request.SymbolCode;
        if (string.IsNullOrWhiteSpace(symbolCode))
        {
            return AnalysisRequestBuildResult.Failure(Results.BadRequest(new AnalysisError(AnalysisEngineErrorCodes.InvalidRequest, "A symbol or symbolCode is required for analysis.")));
        }

        var candleRead = await marketDataService.GetCandlesAsync(symbolCode, timeframe, cancellationToken: cancellationToken);
        if (candleRead.IsFailure || candleRead.Value is null)
        {
            return AnalysisRequestBuildResult.Failure(ToMarketDataErrorResult(candleRead.Error));
        }

        var candleSeries = candleRead.Value;
        if (candleSeries.Candles.Count == 0)
        {
            return AnalysisRequestBuildResult.Failure(Results.BadRequest(new AnalysisError(AnalysisEngineErrorCodes.InvalidRequest, "Market-data provider returned no candles for analysis.")));
        }

        bars = candleSeries.Candles;
        timeframe = candleSeries.Timeframe;
        symbol ??= await ResolveSymbolIdentityAsync(marketDataService, candleSeries, cancellationToken);
    }

    if (symbol is null)
    {
        return AnalysisRequestBuildResult.Failure(Results.BadRequest(new AnalysisError(AnalysisEngineErrorCodes.InvalidRequest, "A symbol identity is required when analysis bars are supplied directly.")));
    }

    return AnalysisRequestBuildResult.Success(new AnalysisRequest(
        symbol,
        timeframe,
        request.RequestedAtUtc ?? DateTimeOffset.UtcNow,
        bars,
        request.EngineId,
        request.StrategyName));
}

static MarketDataSymbolIdentity? CreateSymbolIdentityFromCode(string? symbolCode)
{
    return string.IsNullOrWhiteSpace(symbolCode)
        ? null
        : MarketDataSymbolIdentity.Create(symbolCode, "market-data-provider", null, MarketDataAssetClasses.Stock, "UNKNOWN", "USD");
}

static MarketDataSymbolIdentity? CreateOptionalSymbolIdentity(
    string symbol,
    string? provider,
    string? providerSymbolId,
    string? exchange,
    string? currency,
    string? assetClass)
{
    if (string.IsNullOrWhiteSpace(provider)
        && string.IsNullOrWhiteSpace(providerSymbolId)
        && string.IsNullOrWhiteSpace(exchange)
        && string.IsNullOrWhiteSpace(currency)
        && string.IsNullOrWhiteSpace(assetClass))
    {
        return null;
    }

    return MarketDataSymbolIdentity.Create(
        symbol,
        string.IsNullOrWhiteSpace(provider) ? "market-data-provider" : provider,
        providerSymbolId,
        assetClass,
        exchange,
        currency);
}

static async Task<MarketDataSymbolIdentity> ResolveSymbolIdentityAsync(
    IMarketDataService marketDataService,
    CandleSeriesResponse candleSeries,
    CancellationToken cancellationToken)
{
    var symbolRead = await marketDataService.GetSymbolAsync(candleSeries.Symbol, cancellationToken);
    if (symbolRead.IsSuccess && symbolRead.Value is not null)
    {
        var marketSymbol = symbolRead.Value;
        return MarketDataSymbolIdentity.Create(
            marketSymbol.Symbol,
            candleSeries.Source,
            providerSymbolId: null,
            marketSymbol.AssetClass,
            marketSymbol.Exchange,
            currency: "USD");
    }

    return MarketDataSymbolIdentity.Create(
        candleSeries.Symbol,
        candleSeries.Source,
        providerSymbolId: null,
        MarketDataAssetClasses.Stock,
        exchange: "UNKNOWN",
        currency: "USD");
}

static Task<IResult> GetWorkspaceWatchlistAsync(
    IWorkspaceIdentityProvider identityProvider,
    IWorkspaceWatchlistSchemaInitializer schemaInitializer,
    IWorkspaceWatchlistRepository repository,
    CancellationToken cancellationToken) =>
    ExecuteWatchlistRequestAsync(async () =>
    {
        await schemaInitializer.InitializeAsync(cancellationToken);
        var response = await repository.GetAsync(identityProvider.Current, cancellationToken);
        return Results.Ok(response);
    });

static Task<IResult> ReplaceWorkspaceWatchlistAsync(
    ReplaceWorkspaceWatchlistRequest? request,
    IWorkspaceIdentityProvider identityProvider,
    IWorkspaceWatchlistSchemaInitializer schemaInitializer,
    IWorkspaceWatchlistRepository repository,
    CancellationToken cancellationToken) =>
    ExecuteWatchlistRequestAsync(async () =>
    {
        var symbols = NormalizeReplacementWatchlistRequest(request);
        await schemaInitializer.InitializeAsync(cancellationToken);
        var response = await repository.ReplaceAsync(identityProvider.Current, symbols, cancellationToken);
        return Results.Ok(response);
    });

static Task<IResult> PinWorkspaceWatchlistSymbolAsync(
    WorkspaceWatchlistSymbolInput? symbol,
    IWorkspaceIdentityProvider identityProvider,
    IWorkspaceWatchlistSchemaInitializer schemaInitializer,
    IWorkspaceWatchlistRepository repository,
    CancellationToken cancellationToken) =>
    ExecuteWatchlistRequestAsync(async () =>
    {
        var normalizedSymbol = NormalizePinnedSymbolRequest(symbol);
        await schemaInitializer.InitializeAsync(cancellationToken);
        var response = await repository.PinAsync(identityProvider.Current, normalizedSymbol, cancellationToken);
        return Results.Ok(response);
    });

static Task<IResult> UnpinWorkspaceWatchlistInstrumentAsync(
    string instrumentKey,
    IWorkspaceIdentityProvider identityProvider,
    IWorkspaceWatchlistSchemaInitializer schemaInitializer,
    IWorkspaceWatchlistRepository repository,
    CancellationToken cancellationToken) =>
    ExecuteWatchlistRequestAsync(async () =>
    {
        await schemaInitializer.InitializeAsync(cancellationToken);
        var response = await repository.UnpinByInstrumentKeyAsync(identityProvider.Current, instrumentKey, cancellationToken);
        return Results.Ok(response);
    });

static Task<IResult> UnpinWorkspaceWatchlistSymbolAsync(
    string symbol,
    IWorkspaceIdentityProvider identityProvider,
    IWorkspaceWatchlistSchemaInitializer schemaInitializer,
    IWorkspaceWatchlistRepository repository,
    CancellationToken cancellationToken) =>
    ExecuteWatchlistRequestAsync(async () =>
    {
        var normalizedSymbol = WorkspaceSymbolNormalizer.Normalize(symbol);
        await schemaInitializer.InitializeAsync(cancellationToken);
        var response = await repository.UnpinAsync(identityProvider.Current, normalizedSymbol, cancellationToken);
        return Results.Ok(response);
    });

static async Task<IResult> ExecuteWatchlistRequestAsync(Func<Task<IResult>> operation)
{
    try
    {
        return await operation();
    }
    catch (WorkspaceWatchlistValidationException exception)
    {
        return Results.BadRequest(new WorkspaceWatchlistErrorResponse(exception.Code, exception.Message));
    }
    catch (WorkspaceStorageUnavailableException exception)
    {
        return Results.Json(
            new WorkspaceWatchlistErrorResponse(exception.Code, "Watchlist storage is unavailable."),
            statusCode: StatusCodes.Status503ServiceUnavailable);
    }
}

static WorkspaceWatchlistSymbolInput NormalizePinnedSymbolRequest(WorkspaceWatchlistSymbolInput? symbol)
{
    if (symbol is null)
    {
        throw new WorkspaceWatchlistValidationException(
            WorkspaceWatchlistErrorCodes.InvalidSymbol,
            "A watchlist symbol payload is required.");
    }

    return symbol with { Symbol = WorkspaceSymbolNormalizer.Normalize(symbol.Symbol) };
}

static IReadOnlyList<WorkspaceWatchlistSymbolInput> NormalizeReplacementWatchlistRequest(ReplaceWorkspaceWatchlistRequest? request)
{
    var symbols = request?.Symbols ?? Array.Empty<WorkspaceWatchlistSymbolInput>();
    return symbols.Select(NormalizePinnedSymbolRequest).ToArray();
}

public sealed record AnalysisRunApiRequest(
    MarketDataSymbolIdentity? Symbol,
    string? SymbolCode,
    string? Timeframe,
    DateTimeOffset? RequestedAtUtc,
    IReadOnlyList<OhlcvCandle>? Bars,
    string? EngineId,
    string? StrategyName);

public sealed record ReplaceWorkspaceWatchlistRequest(IReadOnlyList<WorkspaceWatchlistSymbolInput>? Symbols);

public sealed record WorkspaceWatchlistErrorResponse(string Code, string Error);

internal sealed record AnalysisRequestBuildResult(AnalysisRequest? Request, IResult? ErrorResult)
{
    public static AnalysisRequestBuildResult Success(AnalysisRequest request) => new(request, null);

    public static AnalysisRequestBuildResult Failure(IResult errorResult) => new(null, errorResult);
}
