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
    async (AnalysisRunRequest? request, IAnalysisRequestIntake analysisIntake, CancellationToken cancellationToken) =>
        ToAnalysisRunIntakeResult(await analysisIntake.RunAsync(request, cancellationToken)));
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

static IResult ToAnalysisRunIntakeResult(AnalysisRunIntakeResult result)
{
    if (result.MarketDataError is not null)
    {
        return ToMarketDataErrorResult(result.MarketDataError);
    }

    if (result.InvalidRequestError is not null)
    {
        return Results.BadRequest(result.InvalidRequestError);
    }

    return result.Result is not null
        ? ToAnalysisResult(result.Result)
        : Results.BadRequest(new AnalysisError(AnalysisEngineErrorCodes.InvalidRequest, "Analysis request failed."));
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

public sealed record ReplaceWorkspaceWatchlistRequest(IReadOnlyList<WorkspaceWatchlistSymbolInput>? Symbols);

public sealed record WorkspaceWatchlistErrorResponse(string Code, string Error);
