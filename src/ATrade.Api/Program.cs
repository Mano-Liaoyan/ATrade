using ATrade.Accounts;
using ATrade.Brokers;
using ATrade.Brokers.Ibkr;
using ATrade.MarketData;
using ATrade.MarketData.Ibkr;
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
builder.Services.AddIbkrMarketDataProvider();
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
