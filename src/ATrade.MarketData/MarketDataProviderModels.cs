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
    public const string SearchNotSupported = "search-not-supported";
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
    string? ProviderSymbolId,
    string AssetClass,
    string Exchange);

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
    string Sector);

public sealed record MarketDataSymbolSearchResponse(
    DateTimeOffset GeneratedAt,
    IReadOnlyList<MarketDataSymbolSearchResult> Results);
