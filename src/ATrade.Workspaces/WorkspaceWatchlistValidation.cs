using ATrade.MarketData;

namespace ATrade.Workspaces;

public static class WorkspaceWatchlistErrorCodes
{
    public const string InvalidSymbol = "invalid-symbol";
    public const string InvalidInstrumentKey = "invalid-instrument-key";
    public const string AmbiguousSymbol = "ambiguous-symbol";
    public const string StorageUnavailable = "watchlist-storage-unavailable";
}

public sealed class WorkspaceWatchlistValidationException : ArgumentException
{
    public WorkspaceWatchlistValidationException(string code, string message, string? paramName = null)
        : base(message, paramName)
    {
        Code = code;
    }

    public string Code { get; }
}

public static class WorkspaceSymbolNormalizer
{
    public static string Normalize(string symbol)
    {
        if (!TryNormalize(symbol, out var normalizedSymbol, out var error))
        {
            throw new WorkspaceWatchlistValidationException(WorkspaceWatchlistErrorCodes.InvalidSymbol, error, nameof(symbol));
        }

        return normalizedSymbol;
    }

    public static bool TryNormalize(string? symbol, out string normalizedSymbol, out string error) =>
        ExactInstrumentIdentity.TryNormalizeSymbol(symbol, out normalizedSymbol, out error);
}
