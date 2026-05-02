using System.Globalization;
using ATrade.Brokers.Ibkr;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Logging;

namespace ATrade.MarketData.Ibkr;

public sealed class IbkrMarketDataProvider(
    IbkrGatewayOptions gatewayOptions,
    IIbkrSessionReadinessService readinessService,
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

    public MarketDataProviderStatus GetStatus() =>
        throw new NotSupportedException("Synchronous IBKR market-data status reads are no longer supported. Use GetStatusAsync.");

    public async Task<MarketDataProviderStatus> GetStatusAsync(CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var readiness = await readinessService.CheckReadinessAsync(cancellationToken).ConfigureAwait(false);
        return ToMarketDataStatus(readiness);
    }

    public TrendingSymbolsResponse GetTrendingSymbols() =>
        throw new NotSupportedException("Synchronous IBKR trending reads are no longer supported. Use GetTrendingSymbolsAsync.");

    public async Task<MarketDataReadResult<TrendingSymbolsResponse>> GetTrendingSymbolsAsync(CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var status = await GetStatusAsync(cancellationToken).ConfigureAwait(false);
        if (!status.IsAvailable)
        {
            return MarketDataReadResult<TrendingSymbolsResponse>.Failure(status.ToError());
        }

        var scannerRead = await TryExecuteAsync(
            static (client, token) => client.GetTrendingScannerResultsAsync(token),
            marketDataClient,
            cancellationToken).ConfigureAwait(false);
        if (!scannerRead.Succeeded || scannerRead.Result is null)
        {
            var error = scannerRead.Error ?? status.ToError();
            return MarketDataReadResult<TrendingSymbolsResponse>.Failure(error);
        }

        var scannerResults = scannerRead.Result
            .Where(result => !string.IsNullOrWhiteSpace(result.Conid))
            .Take(20)
            .ToArray();
        var snapshots = await GetSnapshotLookupAsync(scannerResults.Select(result => result.Conid).ToArray(), cancellationToken).ConfigureAwait(false);
        var symbols = scannerResults
            .Select((result, index) => CreateTrendingSymbol(result, index + 1, snapshots))
            .ToArray();

        return MarketDataReadResult<TrendingSymbolsResponse>.Success(new TrendingSymbolsResponse(DateTimeOffset.UtcNow, symbols, IbkrMarketDataSource.Scanner));
    }

    public bool TrySearchSymbols(string query, out MarketDataSymbolSearchResponse? response, out MarketDataError? error) =>
        throw new NotSupportedException("Synchronous IBKR symbol search is no longer supported. Use SearchSymbolsAsync.");

    public async Task<MarketDataReadResult<MarketDataSymbolSearchResponse>> SearchSymbolsAsync(string query, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (string.IsNullOrWhiteSpace(query))
        {
            return MarketDataReadResult<MarketDataSymbolSearchResponse>.Failure(new MarketDataError("invalid-query", "A non-empty symbol search query is required."));
        }

        var availabilityError = await GetAvailabilityErrorAsync(cancellationToken).ConfigureAwait(false);
        if (availabilityError is not null)
        {
            return MarketDataReadResult<MarketDataSymbolSearchResponse>.Failure(availabilityError);
        }

        var contractsRead = await TryExecuteAsync(
            static (state, token) => state.Client.SearchContractsAsync(state.Query, token),
            (Client: marketDataClient, Query: query),
            cancellationToken).ConfigureAwait(false);
        if (!contractsRead.Succeeded || contractsRead.Result is null)
        {
            return MarketDataReadResult<MarketDataSymbolSearchResponse>.Failure(ToReadError(contractsRead.Error));
        }

        var response = new MarketDataSymbolSearchResponse(
            DateTimeOffset.UtcNow,
            contractsRead.Result
                .Take(MarketDataSymbolSearchLimits.MaximumLimit)
                .Select(contract => new MarketDataSymbolSearchResult(
                    CreateIdentity(contract),
                    contract.Name,
                    contract.Sector))
                .ToArray(),
            IbkrMarketDataSource.Provider);
        return MarketDataReadResult<MarketDataSymbolSearchResponse>.Success(response);
    }

    public bool TryGetSymbol(string symbol, out MarketDataSymbol? marketSymbol) =>
        throw new NotSupportedException("Synchronous IBKR symbol lookup is no longer supported. Use GetSymbolAsync.");

    public async Task<MarketDataReadResult<MarketDataSymbol>> GetSymbolAsync(string symbol, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var availabilityError = await GetAvailabilityErrorAsync(cancellationToken).ConfigureAwait(false);
        if (availabilityError is not null)
        {
            return MarketDataReadResult<MarketDataSymbol>.Failure(availabilityError);
        }

        var contractRead = await ResolveContractAsync(symbol, identity: null, cancellationToken).ConfigureAwait(false);
        if (!contractRead.Succeeded || contractRead.Result is null)
        {
            return MarketDataReadResult<MarketDataSymbol>.Failure(ToReadError(contractRead.Error));
        }

        var snapshotLookup = await GetSnapshotLookupAsync(new[] { contractRead.Result.Conid }, cancellationToken).ConfigureAwait(false);
        var snapshot = FindSnapshot(contractRead.Result, snapshotLookup);
        return MarketDataReadResult<MarketDataSymbol>.Success(CreateMarketDataSymbol(contractRead.Result, snapshot));
    }

    public bool TryGetCandles(string symbol, string? timeframe, out CandleSeriesResponse? response, out MarketDataError? error, MarketDataSymbolIdentity? identity = null) =>
        throw new NotSupportedException("Synchronous IBKR candle reads are no longer supported. Use GetCandlesAsync.");

    public async Task<MarketDataReadResult<CandleSeriesResponse>> GetCandlesAsync(
        string symbol,
        string? timeframe,
        MarketDataSymbolIdentity? identity = null,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var availabilityError = await GetAvailabilityErrorAsync(cancellationToken).ConfigureAwait(false);
        if (availabilityError is not null)
        {
            return MarketDataReadResult<CandleSeriesResponse>.Failure(availabilityError);
        }

        if (!TryMapTimeframe(timeframe, out var definition, out var period, out var barSize, out var error))
        {
            return MarketDataReadResult<CandleSeriesResponse>.Failure(error!);
        }

        var contractRead = await ResolveContractAsync(symbol, identity, cancellationToken).ConfigureAwait(false);
        if (!contractRead.Succeeded || contractRead.Result is null)
        {
            return MarketDataReadResult<CandleSeriesResponse>.Failure(ToReadError(contractRead.Error));
        }

        var barsRead = await TryExecuteAsync(
            static (state, token) => state.Client.GetHistoricalBarsAsync(state.Conid, state.Period, state.BarSize, token),
            (Client: marketDataClient, Conid: contractRead.Result.Conid, Period: period, BarSize: barSize),
            cancellationToken).ConfigureAwait(false);
        if (!barsRead.Succeeded || barsRead.Result is null)
        {
            return MarketDataReadResult<CandleSeriesResponse>.Failure(ToReadError(barsRead.Error));
        }

        var candles = barsRead.Result
            .Select(bar => new OhlcvCandle(bar.Time, bar.Open, bar.High, bar.Low, bar.Close, bar.Volume))
            .TakeLast(definition.CandleCount)
            .ToArray();
        if (candles.Length == 0)
        {
            return MarketDataReadResult<CandleSeriesResponse>.Failure(new MarketDataError("history-unavailable", $"IBKR iBeam returned no historical bars for {contractRead.Result.Symbol}."));
        }

        return MarketDataReadResult<CandleSeriesResponse>.Success(new CandleSeriesResponse(
            contractRead.Result.Symbol,
            definition.Name,
            DateTimeOffset.UtcNow,
            candles,
            IbkrMarketDataSource.History,
            CreateIdentity(contractRead.Result)));
    }

    public bool TryGetIndicators(string symbol, string? timeframe, out IndicatorResponse? response, out MarketDataError? error, MarketDataSymbolIdentity? identity = null) =>
        throw new NotSupportedException("Synchronous IBKR indicator reads are no longer supported. Use GetIndicatorsAsync.");

    public async Task<MarketDataReadResult<IndicatorResponse>> GetIndicatorsAsync(
        string symbol,
        string? timeframe,
        MarketDataSymbolIdentity? identity = null,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var candleRead = await GetCandlesAsync(symbol, timeframe, identity, cancellationToken).ConfigureAwait(false);
        if (!candleRead.IsSuccess || candleRead.Value is null)
        {
            return MarketDataReadResult<IndicatorResponse>.Failure(ToReadError(candleRead.Error));
        }

        var response = indicatorService.Calculate(candleRead.Value.Symbol, candleRead.Value.Timeframe, candleRead.Value.Candles, candleRead.Value.Identity) with
        {
            Source = candleRead.Value.Source,
        };
        return MarketDataReadResult<IndicatorResponse>.Success(response);
    }

    public bool TryGetLatestUpdate(string symbol, string? timeframe, out MarketDataUpdate? update, out MarketDataError? error, MarketDataSymbolIdentity? identity = null) =>
        throw new NotSupportedException("Synchronous IBKR latest-update reads are no longer supported. Use GetLatestUpdateAsync.");

    public async Task<MarketDataReadResult<MarketDataUpdate>> GetLatestUpdateAsync(
        string symbol,
        string? timeframe,
        MarketDataSymbolIdentity? identity = null,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var availabilityError = await GetAvailabilityErrorAsync(cancellationToken).ConfigureAwait(false);
        if (availabilityError is not null)
        {
            return MarketDataReadResult<MarketDataUpdate>.Failure(availabilityError);
        }

        if (!MarketDataTimeframes.TryGetDefinition(timeframe, out var definition))
        {
            return MarketDataReadResult<MarketDataUpdate>.Failure(new MarketDataError(
                "unsupported-timeframe",
                $"Timeframe '{timeframe}' is not supported. Supported values: {string.Join(", ", MarketDataTimeframes.Supported)}."));
        }

        var contractRead = await ResolveContractAsync(symbol, identity, cancellationToken).ConfigureAwait(false);
        if (!contractRead.Succeeded || contractRead.Result is null)
        {
            return MarketDataReadResult<MarketDataUpdate>.Failure(ToReadError(contractRead.Error));
        }

        var snapshotsRead = await TryExecuteAsync(
            static (state, token) => state.Client.GetSnapshotsAsync(new[] { state.Conid }, token),
            (Client: marketDataClient, Conid: contractRead.Result.Conid),
            cancellationToken).ConfigureAwait(false);
        if (!snapshotsRead.Succeeded || snapshotsRead.Result is null)
        {
            return MarketDataReadResult<MarketDataUpdate>.Failure(ToReadError(snapshotsRead.Error));
        }

        var snapshot = FindSnapshot(contractRead.Result, snapshotsRead.Result.ToDictionary(snapshot => snapshot.Conid, StringComparer.OrdinalIgnoreCase));
        if (snapshot?.LastPrice is null)
        {
            return MarketDataReadResult<MarketDataUpdate>.Failure(new MarketDataError("snapshot-unavailable", $"IBKR iBeam returned no latest market-data snapshot for {contractRead.Result.Symbol}."));
        }

        var last = Round(snapshot.LastPrice.Value);
        return MarketDataReadResult<MarketDataUpdate>.Success(new MarketDataUpdate(
            contractRead.Result.Symbol,
            definition.Name,
            snapshot.ObservedAtUtc,
            Round(snapshot.Open ?? last),
            Round(snapshot.High ?? last),
            Round(snapshot.Low ?? last),
            last,
            snapshot.Volume ?? 0,
            Round(snapshot.ChangePercent ?? 0m),
            IbkrMarketDataSource.Snapshot,
            CreateIdentity(contractRead.Result)));
    }

    public bool TryCreateSnapshot(string symbol, string? timeframe, out MarketDataUpdate? update, out MarketDataError? error) =>
        throw new NotSupportedException("Synchronous IBKR streaming snapshots are no longer supported. Use CreateSnapshotAsync.");

    public Task<MarketDataReadResult<MarketDataUpdate>> CreateSnapshotAsync(
        string symbol,
        string? timeframe,
        CancellationToken cancellationToken = default) =>
        GetLatestUpdateAsync(symbol, timeframe, identity: null, cancellationToken);

    public string GetGroupName(string symbol, string timeframe) => $"market-data:ibkr:{symbol.Trim().ToUpperInvariant()}:{timeframe}";

    private static MarketDataProviderStatus ToMarketDataStatus(IbkrSessionReadinessResult readiness) => readiness.State switch
    {
        IbkrSessionReadinessStates.Authenticated when readiness.IsReady => MarketDataProviderStatus.Available(ProviderIdentity, ProviderCapabilities),
        IbkrSessionReadinessStates.Disabled => MarketDataProviderStatus.NotConfigured(
            ProviderIdentity,
            ProviderCapabilities,
            "IBKR iBeam market data is disabled. Enable ATRADE_BROKER_INTEGRATION_ENABLED and configure the ignored local .env to use real market data."),
        IbkrSessionReadinessStates.CredentialsMissing => MarketDataProviderStatus.NotConfigured(
            ProviderIdentity,
            ProviderCapabilities,
            "IBKR iBeam market data requires the ATrade IBKR username, password, and paper account id variables in the ignored local .env."),
        IbkrSessionReadinessStates.NotConfigured when !readiness.HasGatewayBaseUrl => MarketDataProviderStatus.NotConfigured(
            ProviderIdentity,
            ProviderCapabilities,
            $"IBKR iBeam market data requires an absolute {IbkrGatewayEnvironmentVariables.GatewayUrl}."),
        IbkrSessionReadinessStates.NotConfigured => MarketDataProviderStatus.NotConfigured(
            ProviderIdentity,
            ProviderCapabilities,
            $"IBKR iBeam market data requires {IbkrGatewayEnvironmentVariables.GatewayImage}={IbkrGatewayContainerOptions.DefaultIbeamImage} and a valid {IbkrGatewayEnvironmentVariables.GatewayPort}."),
        IbkrSessionReadinessStates.Connecting or IbkrSessionReadinessStates.Degraded => MarketDataProviderStatus.Unavailable(
            ProviderIdentity,
            ProviderCapabilities,
            CreateUnauthenticatedStatusMessage(readiness.Message)),
        IbkrSessionReadinessStates.Error => MarketDataProviderStatus.Unavailable(
            ProviderIdentity,
            ProviderCapabilities,
            "IBKR iBeam market-data status check failed safely."),
        _ => MarketDataProviderStatus.Unavailable(
            ProviderIdentity,
            ProviderCapabilities,
            readiness.Message ?? IbkrGatewayTransport.CreateTransportUnavailableMessage()),
    };

    private static string CreateUnauthenticatedStatusMessage(string? message) => string.IsNullOrWhiteSpace(message)
        ? "IBKR iBeam is reachable but the Client Portal session is not authenticated."
        : $"IBKR iBeam is reachable but is not authenticated: {message}";

    private async Task<MarketDataError?> GetAvailabilityErrorAsync(CancellationToken cancellationToken)
    {
        var status = await GetStatusAsync(cancellationToken).ConfigureAwait(false);
        return status.IsAvailable ? null : status.ToError();
    }

    private async Task<ProviderRead<IbkrContract>> ResolveContractAsync(
        string symbol,
        MarketDataSymbolIdentity? identity,
        CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (string.IsNullOrWhiteSpace(symbol))
        {
            return ProviderRead<IbkrContract>.Failure(new MarketDataError(MarketDataProviderErrorCodes.UnsupportedSymbol, "A non-empty symbol is required."));
        }

        var contractsRead = await TryExecuteAsync(
            static (state, token) => state.Client.SearchContractsAsync(state.Symbol, token),
            (Client: marketDataClient, Symbol: symbol),
            cancellationToken).ConfigureAwait(false);
        if (!contractsRead.Succeeded || contractsRead.Result is null)
        {
            return ProviderRead<IbkrContract>.Failure(ToReadError(contractsRead.Error));
        }

        var normalizedSymbol = symbol.Trim().ToUpperInvariant();
        var requestedProviderSymbolId = string.Equals(identity?.Provider, ProviderIdentity.Provider, StringComparison.OrdinalIgnoreCase)
            ? identity?.ProviderSymbolId
            : null;
        var found = !string.IsNullOrWhiteSpace(requestedProviderSymbolId)
            ? contractsRead.Result.FirstOrDefault(candidate => string.Equals(candidate.Conid, requestedProviderSymbolId, StringComparison.OrdinalIgnoreCase))
            : null;
        found ??= contractsRead.Result.FirstOrDefault(candidate => string.Equals(candidate.Symbol, normalizedSymbol, StringComparison.OrdinalIgnoreCase))
            ?? contractsRead.Result.FirstOrDefault();
        if (found is null)
        {
            return ProviderRead<IbkrContract>.Failure(new MarketDataError(MarketDataProviderErrorCodes.UnsupportedSymbol, $"IBKR iBeam returned no stock contract for '{symbol}'."));
        }

        if (!string.IsNullOrWhiteSpace(requestedProviderSymbolId)
            && !string.Equals(found.Conid, requestedProviderSymbolId, StringComparison.OrdinalIgnoreCase))
        {
            return ProviderRead<IbkrContract>.Failure(new MarketDataError(MarketDataProviderErrorCodes.UnsupportedSymbol, $"IBKR iBeam returned no contract {requestedProviderSymbolId} for '{symbol}'."));
        }

        return ProviderRead<IbkrContract>.Success(found);
    }

    private async Task<Dictionary<string, IbkrMarketDataSnapshot>> GetSnapshotLookupAsync(IReadOnlyList<string> conids, CancellationToken cancellationToken)
    {
        if (conids.Count == 0)
        {
            return new Dictionary<string, IbkrMarketDataSnapshot>(StringComparer.OrdinalIgnoreCase);
        }

        var snapshotsRead = await TryExecuteAsync(
            static (state, token) => state.Client.GetSnapshotsAsync(state.Conids, token),
            (Client: marketDataClient, Conids: conids),
            cancellationToken).ConfigureAwait(false);
        return snapshotsRead.Succeeded && snapshotsRead.Result is not null
            ? snapshotsRead.Result
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
            snapshot?.Volume ?? 0,
            CreateIdentity(contract));
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
            },
            CreateIdentity(result));
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

    private async Task<ProviderRead<T>> TryExecuteAsync<TState, T>(
        Func<TState, CancellationToken, Task<T>> operation,
        TState state,
        CancellationToken cancellationToken)
    {
        try
        {
            var result = await operation(state, cancellationToken).ConfigureAwait(false);
            return ProviderRead<T>.Success(result);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch (TaskCanceledException exception)
        {
            var message = RedactConfiguredValues(exception.Message);
            logger.LogWarning("IBKR iBeam market-data request timed out over local HTTPS transport: {Diagnostic}", message);
            return ProviderRead<T>.Failure(new MarketDataError(MarketDataProviderErrorCodes.ProviderUnavailable, IbkrGatewayTransport.CreateTransportTimeoutMessage()));
        }
        catch (IbkrMarketDataProviderException exception)
        {
            var message = RedactConfiguredValues(exception.Message);
            logger.LogWarning("IBKR iBeam market-data request failed safely: {Diagnostic}", message);
            return ProviderRead<T>.Failure(new MarketDataError(exception.Code, message));
        }
        catch (HttpRequestException exception)
        {
            logger.LogWarning(
                "IBKR iBeam market-data request could not reach the local HTTPS gateway transport: {Diagnostic}",
                RedactConfiguredValues(exception.Message));
            return ProviderRead<T>.Failure(new MarketDataError(MarketDataProviderErrorCodes.ProviderUnavailable, IbkrGatewayTransport.CreateTransportUnavailableMessage()));
        }
        catch (Exception exception)
        {
            var message = RedactConfiguredValues(exception.Message);
            logger.LogWarning("IBKR iBeam market-data request failed safely: {Diagnostic}", message);
            return ProviderRead<T>.Failure(new MarketDataError(MarketDataProviderErrorCodes.ProviderUnavailable, "IBKR iBeam market-data request failed safely."));
        }
    }

    private static MarketDataError ToReadError(MarketDataError? error) => error ?? new MarketDataError(
        MarketDataProviderErrorCodes.MarketDataRequestFailed,
        "IBKR iBeam market-data request failed safely.");

    private string RedactConfiguredValues(string? message) => IbkrGatewayDiagnostics.RedactConfiguredValues(message, gatewayOptions);

    private static MarketDataSymbolIdentity CreateIdentity(IbkrContract contract) => MarketDataSymbolIdentity.Create(
        contract.Symbol,
        ProviderIdentity.Provider,
        contract.Conid,
        contract.AssetClass,
        contract.Exchange,
        contract.Currency,
        TryParseIbkrConid(contract.Conid));

    private static MarketDataSymbolIdentity CreateIdentity(IbkrScannerResult result) => MarketDataSymbolIdentity.Create(
        result.Symbol,
        ProviderIdentity.Provider,
        result.Conid,
        result.AssetClass,
        result.Exchange,
        currency: null,
        ibkrConid: TryParseIbkrConid(result.Conid));

    private static long? TryParseIbkrConid(string? conid) =>
        long.TryParse(conid, NumberStyles.Integer, CultureInfo.InvariantCulture, out var value) ? value : null;

    private static decimal Round(decimal value) => decimal.Round(value, 4, MidpointRounding.AwayFromZero);

    private readonly record struct ProviderRead<T>(bool Succeeded, T? Result, MarketDataError? Error)
    {
        public static ProviderRead<T> Success(T result) => new(true, result, null);

        public static ProviderRead<T> Failure(MarketDataError error) => new(false, default, error);
    }
}

public static class IbkrMarketDataServiceCollectionExtensions
{
    public static IServiceCollection AddIbkrMarketDataProvider(this IServiceCollection services)
    {
        ArgumentNullException.ThrowIfNull(services);

        services.TryAddSingleton<IndicatorService>();
        services.TryAddSingleton<IIbkrPaperTradingGuard, IbkrPaperTradingGuard>();
        services.TryAddSingleton<IIbkrSessionReadinessService, IbkrSessionReadinessService>();
        services.AddHttpClient<IIbkrGatewayClient, IbkrGatewayClient>((serviceProvider, client) =>
        {
            var options = serviceProvider.GetRequiredService<IbkrGatewayOptions>();
            IbkrGatewayTransport.ConfigureHttpClient(client, options);
        })
        .ConfigurePrimaryHttpMessageHandler(serviceProvider =>
        {
            var options = serviceProvider.GetRequiredService<IbkrGatewayOptions>();
            return IbkrGatewayTransport.CreateHttpMessageHandler(options);
        });
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
