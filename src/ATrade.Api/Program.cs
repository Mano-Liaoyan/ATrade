using ATrade.Accounts;
using ATrade.Brokers.Ibkr;
using ATrade.MarketData;
using ATrade.Orders;
using ATrade.ServiceDefaults;

var builder = WebApplication.CreateBuilder(args);

LocalDevelopmentPortContractLoader.ApplyApiHttpPortDefault(builder);
builder.AddServiceDefaults();
builder.Services.AddIbkrBrokerAdapter(builder.Configuration);
builder.Services.AddAccountsModule();
builder.Services.AddOrdersModule();
builder.Services.AddMarketDataModule();
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
app.MapGet("/api/market-data/trending", (IMarketDataService marketDataService) => Results.Ok(marketDataService.GetTrendingSymbols()));
app.MapGet(
    "/api/market-data/{symbol}/candles",
    (string symbol, string? timeframe, IMarketDataService marketDataService) =>
    {
        if (marketDataService.TryGetCandles(symbol, timeframe, out var response, out var error))
        {
            return Results.Ok(response);
        }

        return error?.Code == "unsupported-symbol"
            ? Results.NotFound(error)
            : Results.BadRequest(error);
    });
app.MapGet(
    "/api/market-data/{symbol}/indicators",
    (string symbol, string? timeframe, IMarketDataService marketDataService) =>
    {
        if (marketDataService.TryGetIndicators(symbol, timeframe, out var response, out var error))
        {
            return Results.Ok(response);
        }

        return error?.Code == "unsupported-symbol"
            ? Results.NotFound(error)
            : Results.BadRequest(error);
    });
app.MapGet(
    "/api/broker/ibkr/status",
    async (IIbkrBrokerStatusService brokerStatusService, CancellationToken cancellationToken) =>
        Results.Ok(await brokerStatusService.GetStatusAsync(cancellationToken)));
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

app.MapHub<MarketDataHub>("/hubs/market-data");

app.Run();
