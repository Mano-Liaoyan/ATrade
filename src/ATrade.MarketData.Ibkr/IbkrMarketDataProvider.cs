using ATrade.Brokers.Ibkr;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Logging;

namespace ATrade.MarketData.Ibkr;

public sealed class IbkrMarketDataProvider(
    IbkrGatewayOptions gatewayOptions,
    IIbkrPaperTradingGuard paperTradingGuard,
    IIbkrMarketDataClient marketDataClient,
    IndicatorService indicatorService,
    ILogger<IbkrMarketDataProvider> logger) : IMarketDataProvider, IMarketDataStreamingProvider
{
    public static MarketDataProviderIdentity ProviderIdentity { get; } = MarketDataProviderIdentity.Create("ibkr", "Interactive Brokers iBeam market data");

    public static MarketDataProviderCapabilities ProviderCapabilities { get; } = new(
        SupportsTrendingScanner: true,
        SupportsHistoricalCandles: true,
        SupportsIndicators: true,
        SupportsStreamingSnapshots: true,
        SupportsSymbolSearch: true,
        UsesMockData: false);

    public MarketDataProviderIdentity Identity => ProviderIdentity;

    public MarketDataProviderCapabilities Capabilities => ProviderCapabilities;

    public MarketDataProviderStatus GetStatus()
    {
        var guardResult = paperTradingGuard.Evaluate();
        if (!guardResult.IsAllowed)
        {
            return MarketDataProviderStatus.Unavailable(Identity, Capabilities, guardResult.Message);
        }

        if (!gatewayOptions.IntegrationEnabled)
        {
            return MarketDataProviderStatus.NotConfigured(
                Identity,
                Capabilities,
                "IBKR iBeam market data is disabled. Enable ATRADE_BROKER_INTEGRATION_ENABLED and configure the ignored local .env to use real market data.");
        }

        if (!gatewayOptions.HasConfiguredCredentials || !gatewayOptions.HasConfiguredPaperAccountId)
        {
            return MarketDataProviderStatus.NotConfigured(
                Identity,
                Capabilities,
                "IBKR iBeam market data requires the ATrade IBKR username, password, and paper account id variables in the ignored local .env.");
        }

        if (!gatewayOptions.HasConfiguredIbeamContainer)
        {
            return MarketDataProviderStatus.NotConfigured(
                Identity,
                Capabilities,
                $"IBKR iBeam market data requires {IbkrGatewayEnvironmentVariables.GatewayImage}={IbkrGatewayContainerOptions.DefaultIbeamImage} and a valid {IbkrGatewayEnvironmentVariables.GatewayPort}.");
        }

        if (gatewayOptions.GatewayBaseUrl is null)
        {
            return MarketDataProviderStatus.NotConfigured(
                Identity,
                Capabilities,
                $"IBKR iBeam market data requires an absolute {IbkrGatewayEnvironmentVariables.GatewayUrl}.");
        }

        try
        {
            var authStatus = Run(cancellationToken => marketDataClient.GetAuthStatusAsync(cancellationToken));
            if (!authStatus.Authenticated || !authStatus.Connected)
            {
                var message = string.IsNullOrWhiteSpace(authStatus.Message)
                    ? "IBKR iBeam is reachable but the Client Portal session is not authenticated."
                    : $"IBKR iBeam is reachable but is not authenticated: {authStatus.Message}";
                return MarketDataProviderStatus.Unavailable(Identity, Capabilities, message);
            }

            return MarketDataProviderStatus.Available(Identity, Capabilities);
        }
        catch (TaskCanceledException exception)
        {
            logger.LogWarning(exception, "IBKR iBeam market-data status request timed out over local HTTPS transport.");
            return MarketDataProviderStatus.Unavailable(
                Identity,
                Capabilities,
                IbkrGatewayTransport.CreateTransportTimeoutMessage());
        }
        catch (OperationCanceledException)
        {
            throw;
        }
        catch (IbkrMarketDataProviderException exception)
        {
            var message = RedactConfiguredValues(exception.Message);
            logger.LogWarning("IBKR iBeam market-data status check failed safely: {Diagnostic}", message);
            return MarketDataProviderStatus.Unavailable(Identity, Capabilities, message);
        }
        catch (HttpRequestException exception)
        {
            logger.LogWarning(
                "IBKR iBeam market-data status endpoint is not reachable over local HTTPS transport: {Diagnostic}",
                RedactConfiguredValues(exception.Message));
            return MarketDataProviderStatus.Unavailable(
                Identity,
                Capabilities,
                IbkrGatewayTransport.CreateTransportUnavailableMessage());
        }
        catch (Exception exception)
        {
            logger.LogWarning(exception, "IBKR iBeam market-data status check failed safely.");
            return MarketDataProviderStatus.Unavailable(Identity, Capabilities, "IBKR iBeam market-data status check failed safely.");
        }
    }

    public TrendingSymbolsResponse GetTrendingSymbols()
    {
        var status = GetStatus();
        if (!status.IsAvailable)
        {
            throw new MarketDataProviderUnavailableException(status);
        }

        if (!TryExecute(() => marketDataClient.GetTrendingScannerResultsAsync(), out var scannerResponse, out var scannerError) || scannerResponse is null)
        {
            var error = scannerError ?? status.ToError();
            throw new MarketDataProviderUnavailableException(
                MarketDataProviderStatus.Unavailable(Identity, Capabilities, error.Message),
                error);
        }

        var scannerResults = scannerResponse
            .Where(result => !string.IsNullOrWhiteSpace(result.Conid))
            .Take(20)
            .ToArray();
        var snapshots = GetSnapshotLookup(scannerResults.Select(result => result.Conid).ToArray());
        var symbols = scannerResults
            .Select((result, index) => CreateTrendingSymbol(result, index + 1, snapshots))
            .ToArray();

        return new TrendingSymbolsResponse(DateTimeOffset.UtcNow, symbols, IbkrMarketDataSource.Scanner);
    }

    public bool TrySearchSymbols(string query, out MarketDataSymbolSearchResponse? response, out MarketDataError? error)
    {
        response = null;
        if (string.IsNullOrWhiteSpace(query))
        {
            error = new MarketDataError("invalid-query", "A non-empty symbol search query is required.");
            return false;
        }

        if (!TryEnsureAvailable(out error))
        {
            return false;
        }

        if (!TryExecute(() => marketDataClient.SearchContractsAsync(query), out var contracts, out error) || contracts is null)
        {
            return false;
        }

        response = new MarketDataSymbolSearchResponse(
            DateTimeOffset.UtcNow,
            contracts
                .Take(MarketDataSymbolSearchLimits.MaximumLimit)
                .Select(contract => new MarketDataSymbolSearchResult(
                    new MarketDataSymbolIdentity(
                        contract.Symbol,
                        Identity.Provider,
                        contract.Conid,
                        contract.AssetClass,
                        contract.Exchange,
                        contract.Currency),
                    contract.Name,
                    contract.Sector))
                .ToArray(),
            IbkrMarketDataSource.Provider);
        return true;
    }

    public bool TryGetSymbol(string symbol, out MarketDataSymbol? marketSymbol)
    {
        marketSymbol = null;
        if (string.IsNullOrWhiteSpace(symbol) || !TryEnsureAvailable(out _))
        {
            return false;
        }

        if (!TryResolveContract(symbol, out var contract, out _))
        {
            return false;
        }

        var snapshotLookup = GetSnapshotLookup(new[] { contract.Conid });
        var snapshot = FindSnapshot(contract, snapshotLookup);
        marketSymbol = CreateMarketDataSymbol(contract, snapshot);
        return true;
    }

    public bool TryGetCandles(string symbol, string? timeframe, out CandleSeriesResponse? response, out MarketDataError? error)
    {
        response = null;
        if (!TryEnsureAvailable(out error))
        {
            return false;
        }

        if (!TryMapTimeframe(timeframe, out var definition, out var period, out var barSize, out error))
        {
            return false;
        }

        if (!TryResolveContract(symbol, out var contract, out error))
        {
            return false;
        }

        if (!TryExecute(() => marketDataClient.GetHistoricalBarsAsync(contract.Conid, period, barSize), out var bars, out error) || bars is null)
        {
            return false;
        }

        var candles = bars
            .Select(bar => new OhlcvCandle(bar.Time, bar.Open, bar.High, bar.Low, bar.Close, bar.Volume))
            .TakeLast(definition.CandleCount)
            .ToArray();
        if (candles.Length == 0)
        {
            error = new MarketDataError("history-unavailable", $"IBKR iBeam returned no historical bars for {contract.Symbol}.");
            return false;
        }

        response = new CandleSeriesResponse(contract.Symbol, definition.Name, DateTimeOffset.UtcNow, candles, IbkrMarketDataSource.History);
        return true;
    }

    public bool TryGetIndicators(string symbol, string? timeframe, out IndicatorResponse? response, out MarketDataError? error)
    {
        response = null;
        if (!TryGetCandles(symbol, timeframe, out var candleResponse, out error) || candleResponse is null)
        {
            return false;
        }

        response = indicatorService.Calculate(candleResponse.Symbol, candleResponse.Timeframe, candleResponse.Candles) with
        {
            Source = candleResponse.Source,
        };
        return true;
    }

    public bool TryGetLatestUpdate(string symbol, string? timeframe, out MarketDataUpdate? update, out MarketDataError? error)
    {
        update = null;
        if (!TryEnsureAvailable(out error))
        {
            return false;
        }

        if (!MarketDataTimeframes.TryGetDefinition(timeframe, out var definition))
        {
            error = new MarketDataError(
                "unsupported-timeframe",
                $"Timeframe '{timeframe}' is not supported. Supported values: {string.Join(", ", MarketDataTimeframes.Supported)}.");
            return false;
        }

        if (!TryResolveContract(symbol, out var contract, out error))
        {
            return false;
        }

        if (!TryExecute(() => marketDataClient.GetSnapshotsAsync(new[] { contract.Conid }), out var snapshots, out error) || snapshots is null)
        {
            return false;
        }

        var snapshot = FindSnapshot(contract, snapshots.ToDictionary(snapshot => snapshot.Conid, StringComparer.OrdinalIgnoreCase));
        if (snapshot?.LastPrice is null)
        {
            error = new MarketDataError("snapshot-unavailable", $"IBKR iBeam returned no latest market-data snapshot for {contract.Symbol}.");
            return false;
        }

        var last = Round(snapshot.LastPrice.Value);
        update = new MarketDataUpdate(
            contract.Symbol,
            definition.Name,
            snapshot.ObservedAtUtc,
            Round(snapshot.Open ?? last),
            Round(snapshot.High ?? last),
            Round(snapshot.Low ?? last),
            last,
            snapshot.Volume ?? 0,
            Round(snapshot.ChangePercent ?? 0m),
            IbkrMarketDataSource.Snapshot);
        return true;
    }

    public bool TryCreateSnapshot(string symbol, string? timeframe, out MarketDataUpdate? update, out MarketDataError? error) =>
        TryGetLatestUpdate(symbol, timeframe, out update, out error);

    public string GetGroupName(string symbol, string timeframe) => $"market-data:ibkr:{symbol.Trim().ToUpperInvariant()}:{timeframe}";

    private bool TryEnsureAvailable(out MarketDataError? error)
    {
        var status = GetStatus();
        if (status.IsAvailable)
        {
            error = null;
            return true;
        }

        error = status.ToError();
        return false;
    }

    private bool TryResolveContract(string symbol, out IbkrContract contract, out MarketDataError? error)
    {
        contract = null!;
        error = null;
        if (string.IsNullOrWhiteSpace(symbol))
        {
            error = new MarketDataError("unsupported-symbol", "A non-empty symbol is required.");
            return false;
        }

        if (!TryExecute(() => marketDataClient.SearchContractsAsync(symbol), out var contracts, out error) || contracts is null)
        {
            return false;
        }

        var normalizedSymbol = symbol.Trim().ToUpperInvariant();
        var found = contracts.FirstOrDefault(candidate => string.Equals(candidate.Symbol, normalizedSymbol, StringComparison.OrdinalIgnoreCase))
            ?? contracts.FirstOrDefault();
        if (found is null)
        {
            error = new MarketDataError("unsupported-symbol", $"IBKR iBeam returned no stock contract for '{symbol}'.");
            return false;
        }

        contract = found;
        return true;
    }

    private Dictionary<string, IbkrMarketDataSnapshot> GetSnapshotLookup(IReadOnlyList<string> conids)
    {
        if (conids.Count == 0)
        {
            return new Dictionary<string, IbkrMarketDataSnapshot>(StringComparer.OrdinalIgnoreCase);
        }

        return TryExecute(() => marketDataClient.GetSnapshotsAsync(conids), out var snapshots, out _) && snapshots is not null
            ? snapshots
                .Where(snapshot => !string.IsNullOrWhiteSpace(snapshot.Conid))
                .GroupBy(snapshot => snapshot.Conid, StringComparer.OrdinalIgnoreCase)
                .ToDictionary(group => group.Key, group => group.First(), StringComparer.OrdinalIgnoreCase)
            : new Dictionary<string, IbkrMarketDataSnapshot>(StringComparer.OrdinalIgnoreCase);
    }

    private static IbkrMarketDataSnapshot? FindSnapshot(IbkrContract contract, IReadOnlyDictionary<string, IbkrMarketDataSnapshot> snapshots)
    {
        if (snapshots.TryGetValue(contract.Conid, out var byConid))
        {
            return byConid;
        }

        return snapshots.Values.FirstOrDefault(snapshot => string.Equals(snapshot.Symbol, contract.Symbol, StringComparison.OrdinalIgnoreCase));
    }

    private static MarketDataSymbol CreateMarketDataSymbol(IbkrContract contract, IbkrMarketDataSnapshot? snapshot)
    {
        return new MarketDataSymbol(
            contract.Symbol,
            contract.Name,
            contract.AssetClass,
            contract.Exchange,
            contract.Sector,
            Round(snapshot?.LastPrice ?? 0m),
            Round(snapshot?.ChangePercent ?? 0m),
            snapshot?.Volume ?? 0);
    }

    private static TrendingSymbol CreateTrendingSymbol(
        IbkrScannerResult result,
        int fallbackRank,
        IReadOnlyDictionary<string, IbkrMarketDataSnapshot> snapshots)
    {
        var snapshot = snapshots.TryGetValue(result.Conid, out var foundSnapshot) ? foundSnapshot : null;
        var lastPrice = Round(snapshot?.LastPrice ?? result.LastPrice ?? 0m);
        var changePercent = Round(snapshot?.ChangePercent ?? result.ChangePercent ?? 0m);
        var rank = result.Rank ?? fallbackRank;
        var volume = snapshot?.Volume ?? result.Volume ?? 0;
        var scannerScore = result.Score ?? Math.Max(1m, 101m - rank);
        var score = Round(scannerScore + Math.Abs(changePercent) + Math.Min(25m, volume / 1_000_000m));
        var factors = new TrendingFactorBreakdown(
            VolumeSpike: Round(volume > 0 ? Math.Min(3m, volume / 1_000_000m) : 0m),
            PriceMomentum: changePercent,
            Volatility: Round(Math.Abs(changePercent)),
            ExternalSignal: 0m);

        return new TrendingSymbol(
            result.Symbol,
            result.Name,
            result.AssetClass,
            result.Exchange,
            result.Sector,
            lastPrice,
            changePercent,
            score,
            factors,
            new[]
            {
                $"IBKR scanner {IbkrMarketDataSource.Scanner} rank #{rank}.",
                snapshot is null
                    ? "IBKR snapshot data was not available for this scanner row."
                    : "Latest price and volume are from an IBKR iBeam snapshot.",
            });
    }

    private static bool TryMapTimeframe(
        string? timeframe,
        out TimeframeDefinition definition,
        out string period,
        out string barSize,
        out MarketDataError? error)
    {
        period = string.Empty;
        barSize = string.Empty;
        error = null;
        if (!MarketDataTimeframes.TryGetDefinition(timeframe, out definition))
        {
            error = new MarketDataError(
                "unsupported-timeframe",
                $"Timeframe '{timeframe}' is not supported. Supported values: {string.Join(", ", MarketDataTimeframes.Supported)}.");
            return false;
        }

        (period, barSize) = definition.Name switch
        {
            MarketDataTimeframes.OneMinute => ("2d", "1min"),
            MarketDataTimeframes.FiveMinutes => ("1w", "5min"),
            MarketDataTimeframes.OneHour => ("1m", "1h"),
            _ => ("1y", "1d"),
        };
        return true;
    }

    private bool TryExecute<T>(Func<Task<T>> operation, out T? result, out MarketDataError? error)
    {
        result = default;
        error = null;
        try
        {
            result = operation().ConfigureAwait(false).GetAwaiter().GetResult();
            return true;
        }
        catch (TaskCanceledException exception)
        {
            logger.LogWarning(exception, "IBKR iBeam market-data request timed out over local HTTPS transport.");
            error = new MarketDataError(MarketDataProviderErrorCodes.ProviderUnavailable, IbkrGatewayTransport.CreateTransportTimeoutMessage());
            return false;
        }
        catch (OperationCanceledException)
        {
            throw;
        }
        catch (IbkrMarketDataProviderException exception)
        {
            var message = RedactConfiguredValues(exception.Message);
            logger.LogWarning("IBKR iBeam market-data request failed safely: {Diagnostic}", message);
            error = new MarketDataError(exception.Code, message);
            return false;
        }
        catch (HttpRequestException exception)
        {
            logger.LogWarning(
                "IBKR iBeam market-data request could not reach the local HTTPS gateway transport: {Diagnostic}",
                RedactConfiguredValues(exception.Message));
            error = new MarketDataError(MarketDataProviderErrorCodes.ProviderUnavailable, IbkrGatewayTransport.CreateTransportUnavailableMessage());
            return false;
        }
        catch (Exception exception)
        {
            logger.LogWarning(exception, "IBKR iBeam market-data request failed safely.");
            error = new MarketDataError(MarketDataProviderErrorCodes.ProviderUnavailable, "IBKR iBeam market-data request failed safely.");
            return false;
        }
    }

    private string RedactConfiguredValues(string message)
    {
        var redactedMessage = message;
        foreach (var value in new[]
        {
            gatewayOptions.Username,
            gatewayOptions.Password,
            gatewayOptions.PaperAccountId,
            gatewayOptions.GatewayBaseUrl?.ToString(),
            gatewayOptions.GatewayBaseUrl?.Host,
        })
        {
            if (!string.IsNullOrWhiteSpace(value))
            {
                redactedMessage = redactedMessage.Replace(value, "[redacted]", StringComparison.OrdinalIgnoreCase);
            }
        }

        return redactedMessage;
    }

    private static T Run<T>(Func<CancellationToken, Task<T>> operation) =>
        operation(CancellationToken.None).ConfigureAwait(false).GetAwaiter().GetResult();

    private static decimal Round(decimal value) => decimal.Round(value, 4, MidpointRounding.AwayFromZero);
}

public static class IbkrMarketDataServiceCollectionExtensions
{
    public static IServiceCollection AddIbkrMarketDataProvider(this IServiceCollection services)
    {
        ArgumentNullException.ThrowIfNull(services);

        services.TryAddSingleton<IndicatorService>();
        services.TryAddSingleton<IIbkrPaperTradingGuard, IbkrPaperTradingGuard>();
        services.AddHttpClient<IIbkrMarketDataClient, IbkrMarketDataClient>((serviceProvider, client) =>
        {
            var options = serviceProvider.GetRequiredService<IbkrGatewayOptions>();
            IbkrGatewayTransport.ConfigureHttpClient(client, options);
        })
        .ConfigurePrimaryHttpMessageHandler(serviceProvider =>
        {
            var options = serviceProvider.GetRequiredService<IbkrGatewayOptions>();
            return IbkrGatewayTransport.CreateHttpMessageHandler(options);
        });
        services.AddSingleton<IbkrMarketDataProvider>();
        services.AddSingleton<IMarketDataProvider>(static serviceProvider => serviceProvider.GetRequiredService<IbkrMarketDataProvider>());
        services.AddSingleton<IMarketDataStreamingProvider>(static serviceProvider => serviceProvider.GetRequiredService<IbkrMarketDataProvider>());

        return services;
    }
}
