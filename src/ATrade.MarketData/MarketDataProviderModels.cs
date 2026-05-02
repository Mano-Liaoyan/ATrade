namespace ATrade.MarketData;

public static class MarketDataProviderStates
{
    public const string Available = "available";
    public const string NotConfigured = "not-configured";
    public const string Unavailable = "unavailable";
}

public static class MarketDataProviderErrorCodes
{
    public const string ProviderNotConfigured = "provider-not-configured";
    public const string ProviderUnavailable = "provider-unavailable";
    public const string AuthenticationRequired = "authentication-required";
    public const string SearchNotSupported = "search-not-supported";
    public const string InvalidSearchQuery = "invalid-search-query";
    public const string UnsupportedAssetClass = "unsupported-asset-class";
    public const string InvalidSearchLimit = "invalid-search-limit";
    public const string UnsupportedSymbol = "unsupported-symbol";
    public const string MarketDataRequestFailed = "market-data-error";
}

public static class MarketDataAssetClasses
{
    public const string Stock = "STK";
}

public static class MarketDataSymbolSearchLimits
{
    public const int MinimumQueryLength = 2;
    public const int DefaultLimit = 10;
    public const int MaximumLimit = 20;
}

public sealed record MarketDataProviderIdentity(string Provider, string DisplayName)
{
    public static MarketDataProviderIdentity Create(string provider, string displayName)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(provider);
        ArgumentException.ThrowIfNullOrWhiteSpace(displayName);

        return new MarketDataProviderIdentity(provider.Trim().ToLowerInvariant(), displayName.Trim());
    }
}

public sealed record MarketDataSymbolIdentity(
    string Symbol,
    string Provider,
    string? ProviderSymbolId,
    string AssetClass,
    string Exchange,
    string Currency)
{
    public static MarketDataSymbolIdentity Create(
        string symbol,
        string? provider,
        string? providerSymbolId,
        string? assetClass,
        string? exchange,
        string? currency,
        long? ibkrConid = null) => ExactInstrumentIdentity
            .Create(symbol, provider, providerSymbolId, ibkrConid, exchange, currency, assetClass)
            .ToMarketDataSymbolIdentity();

    public ExactInstrumentIdentity ToExactInstrumentIdentity(long? ibkrConid = null) =>
        ExactInstrumentIdentity.FromMarketDataSymbolIdentity(this, ibkrConid);

    public string InstrumentKey => ToExactInstrumentIdentity().InstrumentKey;
}

public sealed record MarketDataProviderCapabilities(
    bool SupportsTrendingScanner,
    bool SupportsHistoricalCandles,
    bool SupportsIndicators,
    bool SupportsStreamingSnapshots,
    bool SupportsSymbolSearch,
    bool UsesMockData);

public sealed record MarketDataProviderStatus(
    string Provider,
    string State,
    string? Message,
    DateTimeOffset ObservedAtUtc,
    MarketDataProviderCapabilities Capabilities)
{
    public bool IsAvailable => string.Equals(State, MarketDataProviderStates.Available, StringComparison.OrdinalIgnoreCase);

    public static MarketDataProviderStatus Available(MarketDataProviderIdentity identity, MarketDataProviderCapabilities capabilities) => new(
        identity.Provider,
        MarketDataProviderStates.Available,
        Message: null,
        DateTimeOffset.UtcNow,
        capabilities);

    public static MarketDataProviderStatus NotConfigured(MarketDataProviderIdentity identity, MarketDataProviderCapabilities capabilities, string message) => new(
        identity.Provider,
        MarketDataProviderStates.NotConfigured,
        message,
        DateTimeOffset.UtcNow,
        capabilities);

    public static MarketDataProviderStatus Unavailable(MarketDataProviderIdentity identity, MarketDataProviderCapabilities capabilities, string message) => new(
        identity.Provider,
        MarketDataProviderStates.Unavailable,
        message,
        DateTimeOffset.UtcNow,
        capabilities);

    public MarketDataError ToError()
    {
        var code = string.Equals(State, MarketDataProviderStates.NotConfigured, StringComparison.OrdinalIgnoreCase)
            ? MarketDataProviderErrorCodes.ProviderNotConfigured
            : MarketDataProviderErrorCodes.ProviderUnavailable;

        return new MarketDataError(code, Message ?? $"Market-data provider '{Provider}' is {State}.");
    }
}

public sealed record MarketDataSymbolSearchResult(
    MarketDataSymbolIdentity Identity,
    string Name,
    string Sector)
{
    public string Symbol => Identity.Symbol;

    public string Provider => Identity.Provider;

    public string? ProviderSymbolId => Identity.ProviderSymbolId;

    public string AssetClass => Identity.AssetClass;

    public string Exchange => Identity.Exchange;

    public string Currency => Identity.Currency;
}

public sealed record MarketDataSymbolSearchResponse(
    DateTimeOffset GeneratedAt,
    IReadOnlyList<MarketDataSymbolSearchResult> Results,
    string Source = "provider");
