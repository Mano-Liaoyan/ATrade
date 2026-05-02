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
    (IMarketDataService marketDataService) => ExecuteMarketDataRequest(() => Results.Ok(marketDataService.GetTrendingSymbols())));
app.MapGet(
    "/api/market-data/search",
    (string? query, string? assetClass, int? limit, IMarketDataService marketDataService, CancellationToken cancellationToken) =>
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (marketDataService.TrySearchSymbols(query, assetClass, limit, out var response, out var error))
        {
            cancellationToken.ThrowIfCancellationRequested();
            return Results.Ok(response);
        }

        return ToMarketDataErrorResult(error);
    });
app.MapGet(
    "/api/market-data/{symbol}/candles",
    (string symbol, string? timeframe, IMarketDataService marketDataService) =>
    {
        if (marketDataService.TryGetCandles(symbol, timeframe, out var response, out var error))
        {
            return Results.Ok(response);
        }

        return ToMarketDataErrorResult(error);
    });
app.MapGet(
    "/api/market-data/{symbol}/indicators",
    (string symbol, string? timeframe, IMarketDataService marketDataService) =>
    {
        if (marketDataService.TryGetIndicators(symbol, timeframe, out var response, out var error))
        {
            return Results.Ok(response);
        }

        return ToMarketDataErrorResult(error);
    });
app.MapGet(
    "/api/analysis/engines",
    (IAnalysisEngineRegistry analysisEngines) => Results.Ok(analysisEngines.GetEngines()));
app.MapPost(
    "/api/analysis/run",
    async (AnalysisRunApiRequest request, IAnalysisEngineRegistry analysisEngines, IMarketDataService marketDataService, CancellationToken cancellationToken) =>
    {
        if (!TryCreateAnalysisRequest(request, marketDataService, out var analysisRequest, out var errorResult))
        {
            return errorResult;
        }

        cancellationToken.ThrowIfCancellationRequested();
        var result = await analysisEngines.AnalyzeAsync(analysisRequest, cancellationToken);
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

static IResult ExecuteMarketDataRequest(Func<IResult> operation)
{
    try
    {
        return operation();
    }
    catch (MarketDataProviderUnavailableException exception)
    {
        return ToMarketDataErrorResult(exception.Error);
    }
}

static IResult ToMarketDataErrorResult(MarketDataError? error)
{
    if (error is null)
    {
        return Results.BadRequest(new MarketDataError("market-data-error", "Market-data request failed."));
    }

    return error.Code switch
    {
        "unsupported-symbol" => Results.NotFound(error),
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

static bool TryCreateAnalysisRequest(
    AnalysisRunApiRequest? request,
    IMarketDataService marketDataService,
    out AnalysisRequest analysisRequest,
    out IResult errorResult)
{
    analysisRequest = null!;
    errorResult = null!;

    if (request is null)
    {
        errorResult = Results.BadRequest(new AnalysisError(AnalysisEngineErrorCodes.InvalidRequest, "An analysis request payload is required."));
        return false;
    }

    var timeframe = string.IsNullOrWhiteSpace(request.Timeframe) ? MarketDataTimeframes.OneDay : request.Timeframe.Trim();
    var symbol = request.Symbol ?? CreateSymbolIdentityFromCode(request.SymbolCode);
    var bars = request.Bars;

    if (bars is null || bars.Count == 0)
    {
        var symbolCode = symbol?.Symbol ?? request.SymbolCode;
        if (string.IsNullOrWhiteSpace(symbolCode))
        {
            errorResult = Results.BadRequest(new AnalysisError(AnalysisEngineErrorCodes.InvalidRequest, "A symbol or symbolCode is required for analysis."));
            return false;
        }

        if (!marketDataService.TryGetCandles(symbolCode, timeframe, out var candleSeries, out var marketDataError))
        {
            errorResult = ToMarketDataErrorResult(marketDataError);
            return false;
        }

        if (candleSeries is null || candleSeries.Candles.Count == 0)
        {
            errorResult = Results.BadRequest(new AnalysisError(AnalysisEngineErrorCodes.InvalidRequest, "Market-data provider returned no candles for analysis."));
            return false;
        }

        bars = candleSeries.Candles;
        timeframe = candleSeries.Timeframe;
        symbol ??= ResolveSymbolIdentity(marketDataService, candleSeries);
    }

    if (symbol is null)
    {
        errorResult = Results.BadRequest(new AnalysisError(AnalysisEngineErrorCodes.InvalidRequest, "A symbol identity is required when analysis bars are supplied directly."));
        return false;
    }

    analysisRequest = new AnalysisRequest(
        symbol,
        timeframe,
        request.RequestedAtUtc ?? DateTimeOffset.UtcNow,
        bars,
        request.EngineId,
        request.StrategyName);
    return true;
}

static MarketDataSymbolIdentity? CreateSymbolIdentityFromCode(string? symbolCode)
{
    return string.IsNullOrWhiteSpace(symbolCode)
        ? null
        : MarketDataSymbolIdentity.Create(symbolCode, "market-data-provider", null, MarketDataAssetClasses.Stock, "UNKNOWN", "USD");
}

static MarketDataSymbolIdentity ResolveSymbolIdentity(IMarketDataService marketDataService, CandleSeriesResponse candleSeries)
{
    if (marketDataService.TryGetSymbol(candleSeries.Symbol, out var marketSymbol) && marketSymbol is not null)
    {
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
