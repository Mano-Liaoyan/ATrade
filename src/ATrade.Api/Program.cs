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
    async (string symbol, string? range, string? chartRange, string? timeframe, string? provider, string? providerSymbolId, string? exchange, string? currency, string? assetClass, IMarketDataService marketDataService, CancellationToken cancellationToken) =>
    {
        var identity = CreateOptionalSymbolIdentity(symbol, provider, providerSymbolId, exchange, currency, assetClass);
        return ToMarketDataResult(await marketDataService.GetCandlesAsync(symbol, SelectChartRange(range, chartRange, timeframe), identity, cancellationToken));
    });
app.MapGet(
    "/api/market-data/{symbol}/indicators",
    async (string symbol, string? range, string? chartRange, string? timeframe, string? provider, string? providerSymbolId, string? exchange, string? currency, string? assetClass, IMarketDataService marketDataService, CancellationToken cancellationToken) =>
    {
        var identity = CreateOptionalSymbolIdentity(symbol, provider, providerSymbolId, exchange, currency, assetClass);
        return ToMarketDataResult(await marketDataService.GetIndicatorsAsync(symbol, SelectChartRange(range, chartRange, timeframe), identity, cancellationToken));
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

app.MapGet(
    "/api/workspace/watchlist",
    async (IWorkspaceWatchlistIntake watchlistIntake, CancellationToken cancellationToken) =>
        ToWorkspaceWatchlistResult(await watchlistIntake.GetAsync(cancellationToken)));
app.MapPut(
    "/api/workspace/watchlist",
    async (ReplaceWorkspaceWatchlistRequest? request, IWorkspaceWatchlistIntake watchlistIntake, CancellationToken cancellationToken) =>
        ToWorkspaceWatchlistResult(await watchlistIntake.ReplaceAsync(request, cancellationToken)));
app.MapPost(
    "/api/workspace/watchlist",
    async (WorkspaceWatchlistSymbolInput? symbol, IWorkspaceWatchlistIntake watchlistIntake, CancellationToken cancellationToken) =>
        ToWorkspaceWatchlistResult(await watchlistIntake.PinAsync(symbol, cancellationToken)));
app.MapDelete(
    "/api/workspace/watchlist/pins/{instrumentKey}",
    async (string instrumentKey, IWorkspaceWatchlistIntake watchlistIntake, CancellationToken cancellationToken) =>
        ToWorkspaceWatchlistResult(await watchlistIntake.UnpinByInstrumentKeyAsync(instrumentKey, cancellationToken)));
app.MapDelete(
    "/api/workspace/watchlist/{symbol}",
    async (string symbol, IWorkspaceWatchlistIntake watchlistIntake, CancellationToken cancellationToken) =>
        ToWorkspaceWatchlistResult(await watchlistIntake.UnpinBySymbolAsync(symbol, cancellationToken)));

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

static string? SelectChartRange(params string?[] requestedRanges) =>
    requestedRanges.FirstOrDefault(requestedRange => !string.IsNullOrWhiteSpace(requestedRange));

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

static IResult ToWorkspaceWatchlistResult(WorkspaceWatchlistIntakeResult result)
{
    if (result.Response is not null)
    {
        return Results.Ok(result.Response);
    }

    var error = result.Error ?? new WorkspaceWatchlistIntakeError(
        WorkspaceWatchlistErrorCodes.InvalidSymbol,
        "Watchlist request failed.",
        WorkspaceWatchlistIntakeErrorKind.Validation);
    var response = new WorkspaceWatchlistErrorResponse(error.Code, error.Error);

    return error.Kind == WorkspaceWatchlistIntakeErrorKind.StorageUnavailable
        ? Results.Json(response, statusCode: StatusCodes.Status503ServiceUnavailable)
        : Results.BadRequest(response);
}

public sealed record WorkspaceWatchlistErrorResponse(string Code, string Error);
