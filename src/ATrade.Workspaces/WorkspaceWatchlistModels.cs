namespace ATrade.Workspaces;

public static class WorkspaceWatchlistDefaults
{
    public const string ManualProvider = "manual";
    public const string IbkrProvider = "ibkr";
    public const string DefaultCurrency = "USD";
    public const string DefaultAssetClass = "STK";
}

public sealed record WorkspaceWatchlistSymbol(
    string Symbol,
    string Provider,
    string? ProviderSymbolId,
    long? IbkrConid,
    string? Name,
    string? Exchange,
    string? Currency,
    string? AssetClass,
    int SortOrder,
    DateTimeOffset CreatedAtUtc,
    DateTimeOffset UpdatedAtUtc);

public sealed record WorkspaceWatchlistSymbolInput(
    string Symbol,
    string? Provider = null,
    string? ProviderSymbolId = null,
    long? IbkrConid = null,
    string? Name = null,
    string? Exchange = null,
    string? Currency = null,
    string? AssetClass = null);

public sealed record NormalizedWorkspaceWatchlistSymbolInput(
    string Symbol,
    string Provider,
    string? ProviderSymbolId,
    long? IbkrConid,
    string? Name,
    string? Exchange,
    string? Currency,
    string? AssetClass,
    int SortOrder);

public sealed record WorkspaceWatchlistResponse(
    string UserId,
    string WorkspaceId,
    IReadOnlyList<WorkspaceWatchlistSymbol> Symbols);
