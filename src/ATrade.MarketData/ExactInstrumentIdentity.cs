using System.Globalization;
using System.Text.RegularExpressions;

namespace ATrade.MarketData;

public static class ExactInstrumentIdentityProviders
{
    public const string Manual = "manual";
    public const string Ibkr = "ibkr";
}

public static class ExactInstrumentIdentityDefaults
{
    public const string DefaultCurrency = "USD";
    public const string DefaultAssetClass = MarketDataAssetClasses.Stock;
    public const int MaxSymbolLength = 32;
    public const int MaxInstrumentKeyLength = 512;
}

public sealed partial record ExactInstrumentIdentity(
    string Provider,
    string? ProviderSymbolId,
    string Symbol,
    string? Exchange,
    string Currency,
    string AssetClass,
    long? IbkrConid = null)
{
    public static ExactInstrumentIdentity Create(
        string symbol,
        string? provider = null,
        string? providerSymbolId = null,
        long? ibkrConid = null,
        string? exchange = null,
        string? currency = null,
        string? assetClass = null)
    {
        return new ExactInstrumentIdentity(
            NormalizeProvider(provider, ibkrConid),
            NormalizeProviderSymbolId(providerSymbolId, ibkrConid),
            NormalizeSymbol(symbol),
            NormalizeOptionalUpper(exchange),
            NormalizeCurrency(currency),
            NormalizeAssetClass(assetClass),
            ibkrConid);
    }

    public static ExactInstrumentIdentity FromMarketDataSymbolIdentity(MarketDataSymbolIdentity identity, long? ibkrConid = null)
    {
        ArgumentNullException.ThrowIfNull(identity);

        return Create(
            identity.Symbol,
            identity.Provider,
            identity.ProviderSymbolId,
            ibkrConid,
            identity.Exchange,
            identity.Currency,
            identity.AssetClass);
    }

    public string InstrumentKey => CreateInstrumentKey();

    public MarketDataSymbolIdentity ToMarketDataSymbolIdentity() => new(
        Symbol,
        Provider,
        ProviderSymbolId,
        AssetClass,
        Exchange ?? string.Empty,
        Currency);

    public string CreateInstrumentKey()
    {
        return string.Join(
            '|',
            $"provider={EncodeSegment(Provider)}",
            $"providerSymbolId={EncodeSegment(ProviderSymbolId)}",
            $"symbol={EncodeSegment(Symbol)}",
            $"exchange={EncodeSegment(Exchange)}",
            $"currency={EncodeSegment(Currency)}",
            $"assetClass={EncodeSegment(AssetClass)}");
    }

    public static string NormalizeExistingInstrumentKey(string? instrumentKey)
    {
        if (!TryNormalizeExistingInstrumentKey(instrumentKey, out var normalized, out var error))
        {
            throw new ArgumentException(error, nameof(instrumentKey));
        }

        return normalized;
    }

    public static bool TryNormalizeExistingInstrumentKey(string? instrumentKey, out string normalizedInstrumentKey, out string error)
    {
        normalizedInstrumentKey = instrumentKey?.Trim() ?? string.Empty;
        if (string.IsNullOrWhiteSpace(normalizedInstrumentKey))
        {
            error = "An instrument key is required.";
            return false;
        }

        if (normalizedInstrumentKey.Length > ExactInstrumentIdentityDefaults.MaxInstrumentKeyLength)
        {
            error = $"Instrument keys must be {ExactInstrumentIdentityDefaults.MaxInstrumentKeyLength} characters or fewer.";
            return false;
        }

        if (!normalizedInstrumentKey.Contains("=", StringComparison.Ordinal) || !normalizedInstrumentKey.Contains("|", StringComparison.Ordinal))
        {
            error = string.Empty;
            return true;
        }

        var segments = ParseInstrumentKeySegments(normalizedInstrumentKey);
        if (segments.Count == 0)
        {
            error = "Instrument keys must use key=value segments.";
            return false;
        }

        var provider = GetSegmentValue(segments, "provider");
        var providerSymbolId = GetSegmentValue(segments, "providerSymbolId");
        var legacyIbkrConid = GetSegmentValue(segments, "ibkrConid");
        var symbol = GetSegmentValue(segments, "symbol");
        var exchange = GetSegmentValue(segments, "exchange");
        var currency = GetSegmentValue(segments, "currency");
        var assetClass = GetSegmentValue(segments, "assetClass");

        if (string.IsNullOrWhiteSpace(symbol))
        {
            error = "Instrument keys must include a symbol segment.";
            return false;
        }

        long? ibkrConid = null;
        if (!string.IsNullOrWhiteSpace(legacyIbkrConid) && long.TryParse(legacyIbkrConid, NumberStyles.Integer, CultureInfo.InvariantCulture, out var parsedConid))
        {
            ibkrConid = parsedConid;
        }

        try
        {
            normalizedInstrumentKey = Create(
                symbol,
                provider,
                providerSymbolId,
                ibkrConid,
                exchange,
                currency,
                assetClass).InstrumentKey;
        }
        catch (ArgumentException exception)
        {
            error = exception.Message;
            return false;
        }

        error = string.Empty;
        return true;
    }

    public static string NormalizeSymbol(string symbol)
    {
        if (!TryNormalizeSymbol(symbol, out var normalizedSymbol, out var error))
        {
            throw new ArgumentException(error, nameof(symbol));
        }

        return normalizedSymbol;
    }

    public static bool TryNormalizeSymbol(string? symbol, out string normalizedSymbol, out string error)
    {
        normalizedSymbol = string.Empty;

        if (string.IsNullOrWhiteSpace(symbol))
        {
            error = "A symbol is required.";
            return false;
        }

        var candidate = symbol.Trim().ToUpperInvariant();
        if (candidate.Length > ExactInstrumentIdentityDefaults.MaxSymbolLength)
        {
            error = $"Symbols must be {ExactInstrumentIdentityDefaults.MaxSymbolLength} characters or fewer.";
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

    public static string NormalizeProvider(string? provider, long? ibkrConid = null)
    {
        var normalized = NormalizeOptional(provider)?.ToLowerInvariant();
        if (!string.IsNullOrWhiteSpace(normalized))
        {
            return normalized;
        }

        return ibkrConid.HasValue ? ExactInstrumentIdentityProviders.Ibkr : ExactInstrumentIdentityProviders.Manual;
    }

    public static string? NormalizeProviderSymbolId(string? providerSymbolId, long? ibkrConid = null)
    {
        return NormalizeOptional(providerSymbolId)
            ?? (ibkrConid.HasValue ? ibkrConid.Value.ToString(CultureInfo.InvariantCulture) : null);
    }

    public static string? NormalizeExchange(string? exchange) => NormalizeOptionalUpper(exchange);

    public static string NormalizeCurrency(string? currency) =>
        NormalizeOptionalUpper(currency) ?? ExactInstrumentIdentityDefaults.DefaultCurrency;

    public static string NormalizeAssetClass(string? assetClass)
    {
        var normalized = NormalizeOptionalUpper(assetClass);
        if (string.IsNullOrWhiteSpace(normalized))
        {
            return ExactInstrumentIdentityDefaults.DefaultAssetClass;
        }

        return normalized switch
        {
            "STOCK" or "STOCKS" => ExactInstrumentIdentityDefaults.DefaultAssetClass,
            _ => normalized,
        };
    }

    private static string? NormalizeOptionalUpper(string? value) => NormalizeOptional(value)?.ToUpperInvariant();

    private static Dictionary<string, string> ParseInstrumentKeySegments(string instrumentKey)
    {
        var segments = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var segment in instrumentKey.Split('|', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
        {
            var separatorIndex = segment.IndexOf('=', StringComparison.Ordinal);
            if (separatorIndex <= 0)
            {
                continue;
            }

            var key = segment[..separatorIndex].Trim();
            if (string.IsNullOrWhiteSpace(key))
            {
                continue;
            }

            var encodedValue = segment[(separatorIndex + 1)..].Trim();
            segments[key] = Uri.UnescapeDataString(encodedValue);
        }

        return segments;
    }

    private static string? GetSegmentValue(IReadOnlyDictionary<string, string> segments, string key) =>
        segments.TryGetValue(key, out var value) ? NormalizeOptional(value) : null;

    private static string? NormalizeOptional(string? value)
    {
        var normalized = value?.Trim();
        return string.IsNullOrWhiteSpace(normalized) ? null : normalized;
    }

    private static string EncodeSegment(string? value) => Uri.EscapeDataString(value?.Trim() ?? string.Empty);

    [GeneratedRegex("^[A-Z0-9][A-Z0-9._-]{0,31}$", RegexOptions.CultureInvariant)]
    private static partial Regex SymbolPattern();
}
