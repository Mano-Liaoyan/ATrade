using System.Text.RegularExpressions;

namespace ATrade.Workspaces;

public static partial class WorkspaceWatchlistErrorCodes
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

public static partial class WorkspaceSymbolNormalizer
{
    private const int MaxSymbolLength = 32;

    public static string Normalize(string symbol)
    {
        if (!TryNormalize(symbol, out var normalizedSymbol, out var error))
        {
            throw new WorkspaceWatchlistValidationException(WorkspaceWatchlistErrorCodes.InvalidSymbol, error, nameof(symbol));
        }

        return normalizedSymbol;
    }

    public static bool TryNormalize(string? symbol, out string normalizedSymbol, out string error)
    {
        normalizedSymbol = string.Empty;

        if (string.IsNullOrWhiteSpace(symbol))
        {
            error = "A symbol is required.";
            return false;
        }

        var candidate = symbol.Trim().ToUpperInvariant();
        if (candidate.Length > MaxSymbolLength)
        {
            error = $"Symbols must be {MaxSymbolLength} characters or fewer.";
            return false;
        }

        if (!SymbolPattern().IsMatch(candidate))
        {
            error = "Symbols may contain only letters, digits, '.', '-', or '_' and must start with a letter or digit.";
            return false;
        }

        normalizedSymbol = candidate;
        error = string.Empty;
        return true;
    }

    [GeneratedRegex("^[A-Z0-9][A-Z0-9._-]{0,31}$", RegexOptions.CultureInvariant)]
    private static partial Regex SymbolPattern();
}
