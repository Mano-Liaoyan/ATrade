using ATrade.Accounts;
using ATrade.Analysis;
using ATrade.Analysis.Lean;
using ATrade.Backtesting;
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
builder.Services.AddAccountsModule(builder.Configuration);
builder.Services.AddOrdersModule();
builder.Services.AddMarketDataModule();
builder.Services.AddTimescaleMarketDataPersistence(builder.Configuration);
builder.Services.AddAnalysisModule();
builder.Services.AddLeanAnalysisEngine(builder.Configuration);
builder.Services.AddBacktestingModule(builder.Configuration);
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
    "/api/accounts/paper-capital",
    async (IPaperCapitalService paperCapitalService, CancellationToken cancellationToken) =>
        Results.Ok(await paperCapitalService.GetAsync(cancellationToken)));
app.MapPut(
    "/api/accounts/local-paper-capital",
    async (LocalPaperCapitalUpdateRequest? request, IPaperCapitalService paperCapitalService, CancellationToken cancellationToken) =>
        ToPaperCapitalIntakeResult(await paperCapitalService.UpdateLocalAsync(request, cancellationToken)));
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
app.MapPost(
    "/api/backtests",
    async (
        BacktestCreateRequest? request,
        IBacktestRunFactory runFactory,
        IBacktestRunSchemaInitializer schemaInitializer,
        IBacktestRunRepository runRepository,
        CancellationToken cancellationToken) =>
    {
        var createResult = await runFactory.CreateQueuedRunAsync(request, cancellationToken);
        if (!createResult.IsSuccess || createResult.Run is null)
        {
            return ToBacktestErrorResult(createResult.Error);
        }

        try
        {
            await schemaInitializer.InitializeAsync(cancellationToken);
            var savedRun = await runRepository.CreateAsync(createResult.Run, cancellationToken);
            return Results.Accepted($"/api/backtests/{savedRun.Run.Id}", savedRun.Run);
        }
        catch (BacktestStorageUnavailableException)
        {
            return ToBacktestErrorResult(new BacktestError(BacktestErrorCodes.StorageUnavailable, BacktestSafeMessages.StorageUnavailable));
        }
        catch (BacktestValidationException exception)
        {
            return ToBacktestErrorResult(new BacktestError(exception.Code, exception.Message));
        }
    });
app.MapGet(
    "/api/backtests",
    async (
        int? limit,
        IPaperCapitalIdentityProvider identityProvider,
        IBacktestRunSchemaInitializer schemaInitializer,
        IBacktestRunRepository runRepository,
        CancellationToken cancellationToken) =>
    {
        try
        {
            await schemaInitializer.InitializeAsync(cancellationToken);
            var runs = await runRepository.ListAsync(GetBacktestScope(identityProvider), limit ?? BacktestRunRepositoryDefaults.DefaultListLimit, cancellationToken);
            return Results.Ok(runs);
        }
        catch (BacktestStorageUnavailableException)
        {
            return ToBacktestErrorResult(new BacktestError(BacktestErrorCodes.StorageUnavailable, BacktestSafeMessages.StorageUnavailable));
        }
    });
app.MapGet(
    "/api/backtests/{id}",
    async (
        string id,
        IPaperCapitalIdentityProvider identityProvider,
        IBacktestRunSchemaInitializer schemaInitializer,
        IBacktestRunRepository runRepository,
        CancellationToken cancellationToken) =>
    {
        try
        {
            await schemaInitializer.InitializeAsync(cancellationToken);
            var run = await runRepository.GetAsync(GetBacktestScope(identityProvider), id, cancellationToken);
            return run is not null
                ? Results.Ok(run.Run)
                : ToBacktestErrorResult(new BacktestError(BacktestErrorCodes.RunNotFound, BacktestSafeMessages.RunNotFound));
        }
        catch (BacktestStorageUnavailableException)
        {
            return ToBacktestErrorResult(new BacktestError(BacktestErrorCodes.StorageUnavailable, BacktestSafeMessages.StorageUnavailable));
        }
        catch (ArgumentException exception)
        {
            return ToBacktestErrorResult(new BacktestError(BacktestErrorCodes.InvalidPayload, exception.Message));
        }
    });
app.MapPost(
    "/api/backtests/{id}/cancel",
    async (
        string id,
        IPaperCapitalIdentityProvider identityProvider,
        IBacktestRunSchemaInitializer schemaInitializer,
        IBacktestRunRepository runRepository,
        CancellationToken cancellationToken) =>
    {
        try
        {
            await schemaInitializer.InitializeAsync(cancellationToken);
            var scope = GetBacktestScope(identityProvider);
            var existing = await runRepository.GetAsync(scope, id, cancellationToken);
            if (existing is null)
            {
                return ToBacktestErrorResult(new BacktestError(BacktestErrorCodes.RunNotFound, BacktestSafeMessages.RunNotFound));
            }

            if (!BacktestRunStatuses.CanCancel(existing.Run.Status))
            {
                return ToBacktestErrorResult(new BacktestError(
                    BacktestErrorCodes.InvalidStatusTransition,
                    "Backtest run is not queued or running and cannot be cancelled."));
            }

            var cancelled = await runRepository.CancelAsync(scope, id, cancellationToken);
            return Results.Ok((cancelled ?? existing).Run);
        }
        catch (BacktestStorageUnavailableException)
        {
            return ToBacktestErrorResult(new BacktestError(BacktestErrorCodes.StorageUnavailable, BacktestSafeMessages.StorageUnavailable));
        }
        catch (ArgumentException exception)
        {
            return ToBacktestErrorResult(new BacktestError(BacktestErrorCodes.InvalidPayload, exception.Message));
        }
    });
app.MapPost(
    "/api/backtests/{id}/retry",
    async (
        string id,
        IPaperCapitalIdentityProvider identityProvider,
        IBacktestRunFactory runFactory,
        IBacktestRunSchemaInitializer schemaInitializer,
        IBacktestRunRepository runRepository,
        CancellationToken cancellationToken) =>
    {
        try
        {
            await schemaInitializer.InitializeAsync(cancellationToken);
            var scope = GetBacktestScope(identityProvider);
            var source = await runRepository.GetAsync(scope, id, cancellationToken);
            if (source is null)
            {
                return ToBacktestErrorResult(new BacktestError(BacktestErrorCodes.RunNotFound, BacktestSafeMessages.RunNotFound));
            }

            if (!BacktestRunStatuses.CanRetry(source.Run.Status))
            {
                return ToBacktestErrorResult(new BacktestError(
                    BacktestErrorCodes.InvalidStatusTransition,
                    "Backtest run is not failed or cancelled and cannot be retried."));
            }

            var retryRequest = BacktestRequestSnapshots.ToCreateRequest(source.Run.Request);
            var retryCreateResult = await runFactory.CreateQueuedRunAsync(retryRequest, cancellationToken);
            if (!retryCreateResult.IsSuccess || retryCreateResult.Run is null)
            {
                return ToBacktestErrorResult(retryCreateResult.Error);
            }

            var retryRun = await runRepository.CreateRetryAsync(scope, source.Run.Id, retryCreateResult.Run, cancellationToken);
            return retryRun is not null
                ? Results.Accepted($"/api/backtests/{retryRun.Run.Id}", retryRun.Run)
                : ToBacktestErrorResult(new BacktestError(
                    BacktestErrorCodes.InvalidStatusTransition,
                    "Backtest retry source is no longer failed or cancelled."));
        }
        catch (BacktestStorageUnavailableException)
        {
            return ToBacktestErrorResult(new BacktestError(BacktestErrorCodes.StorageUnavailable, BacktestSafeMessages.StorageUnavailable));
        }
        catch (BacktestValidationException exception)
        {
            return ToBacktestErrorResult(new BacktestError(exception.Code, exception.Message));
        }
        catch (ArgumentException exception)
        {
            return ToBacktestErrorResult(new BacktestError(BacktestErrorCodes.InvalidPayload, exception.Message));
        }
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

static IResult ToBacktestErrorResult(BacktestError? error)
{
    var response = error ?? new BacktestError(BacktestErrorCodes.InvalidPayload, "Backtest request failed.");

    return response.Code switch
    {
        BacktestErrorCodes.RunNotFound => Results.NotFound(response),
        BacktestErrorCodes.StorageUnavailable => Results.Json(response, statusCode: StatusCodes.Status503ServiceUnavailable),
        BacktestErrorCodes.CapitalUnavailable or BacktestErrorCodes.InvalidStatusTransition => Results.Conflict(response),
        _ => Results.BadRequest(response),
    };
}

static BacktestWorkspaceScope GetBacktestScope(IPaperCapitalIdentityProvider identityProvider) =>
    BacktestWorkspaceScope.From(identityProvider.Current);

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

static IResult ToPaperCapitalIntakeResult(PaperCapitalIntakeResult result)
{
    if (result.Response is not null)
    {
        return Results.Ok(result.Response);
    }

    var error = result.Error ?? new PaperCapitalIntakeError(
        PaperCapitalErrorCodes.InvalidPayload,
        "Paper capital request failed.");
    var response = new PaperCapitalErrorResponse(error.Code, error.Message);

    return string.Equals(error.Code, PaperCapitalErrorCodes.StorageUnavailable, StringComparison.Ordinal)
        ? Results.Json(response, statusCode: StatusCodes.Status503ServiceUnavailable)
        : Results.BadRequest(response);
}

public sealed record WorkspaceWatchlistErrorResponse(string Code, string Error);

public sealed record PaperCapitalErrorResponse(string Code, string Error);
