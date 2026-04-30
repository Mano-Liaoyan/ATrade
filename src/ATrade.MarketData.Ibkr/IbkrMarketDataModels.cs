using System.Globalization;
using System.Text.Json;

namespace ATrade.MarketData.Ibkr;

public static class IbkrMarketDataSource
{
    public const string Provider = "ibkr";
    public const string Snapshot = "ibkr-ibeam-snapshot";
    public const string History = "ibkr-ibeam-history";
    public const string Scanner = "ibkr-ibeam-scanner:STK.US.MAJOR:TOP_PERC_GAIN";
}

public sealed record IbkrContract(
    string Symbol,
    string Name,
    string AssetClass,
    string Exchange,
    string Conid,
    string Sector,
    string Currency);

public sealed record IbkrMarketDataSnapshot(
    string Conid,
    string Symbol,
    decimal? LastPrice,
    decimal? ChangePercent,
    decimal? Open,
    decimal? High,
    decimal? Low,
    long? Volume,
    DateTimeOffset ObservedAtUtc);

public sealed record IbkrHistoricalBar(
    DateTimeOffset Time,
    decimal Open,
    decimal High,
    decimal Low,
    decimal Close,
    long Volume);

public sealed record IbkrScannerResult(
    string Symbol,
    string Name,
    string AssetClass,
    string Exchange,
    string Conid,
    string Sector,
    int? Rank,
    decimal? Score,
    decimal? LastPrice,
    decimal? ChangePercent,
    long? Volume,
    string Source);

public sealed class IbkrMarketDataProviderException : InvalidOperationException
{
    public IbkrMarketDataProviderException(string code, string message)
        : base(message)
    {
        Code = code;
    }

    public IbkrMarketDataProviderException(string code, string message, Exception innerException)
        : base(message, innerException)
    {
        Code = code;
    }

    public string Code { get; }
}

internal static class IbkrJsonElementExtensions
{
    public static bool TryGetPropertyIgnoreCase(this JsonElement element, string name, out JsonElement property)
    {
        if (element.ValueKind == JsonValueKind.Object)
        {
            foreach (var candidate in element.EnumerateObject())
            {
                if (string.Equals(candidate.Name, name, StringComparison.OrdinalIgnoreCase))
                {
                    property = candidate.Value;
                    return true;
                }
            }
        }

        property = default;
        return false;
    }

    public static bool TryGetNestedPropertyIgnoreCase(this JsonElement element, out JsonElement property, params string[] names)
    {
        var current = element;
        foreach (var name in names)
        {
            if (!current.TryGetPropertyIgnoreCase(name, out current))
            {
                property = default;
                return false;
            }
        }

        property = current;
        return true;
    }

    public static string? GetStringValue(this JsonElement element, params string[] names)
    {
        foreach (var name in names)
        {
            if (element.TryGetPropertyIgnoreCase(name, out var property))
            {
                var value = property.GetScalarString();
                if (!string.IsNullOrWhiteSpace(value))
                {
                    return value.Trim();
                }
            }
        }

        return null;
    }

    public static string? GetNestedStringValue(this JsonElement element, params string[] names)
    {
        if (!element.TryGetNestedPropertyIgnoreCase(out var property, names))
        {
            return null;
        }

        var value = property.GetScalarString();
        return string.IsNullOrWhiteSpace(value) ? null : value.Trim();
    }

    public static string? GetScalarString(this JsonElement element)
    {
        return element.ValueKind switch
        {
            JsonValueKind.String => element.GetString(),
            JsonValueKind.Number => element.GetRawText(),
            JsonValueKind.True => bool.TrueString,
            JsonValueKind.False => bool.FalseString,
            _ => null,
        };
    }

    public static decimal? GetDecimalValue(this JsonElement element, params string[] names)
    {
        foreach (var name in names)
        {
            if (element.TryGetPropertyIgnoreCase(name, out var property) && property.TryGetDecimalValue(out var value))
            {
                return value;
            }
        }

        return null;
    }

    public static long? GetInt64Value(this JsonElement element, params string[] names)
    {
        foreach (var name in names)
        {
            if (element.TryGetPropertyIgnoreCase(name, out var property) && property.TryGetInt64Value(out var value))
            {
                return value;
            }
        }

        return null;
    }

    public static int? GetInt32Value(this JsonElement element, params string[] names)
    {
        var value = element.GetInt64Value(names);
        return value is null ? null : checked((int)value.Value);
    }

    public static bool TryGetDecimalValue(this JsonElement element, out decimal value)
    {
        value = 0m;
        if (element.ValueKind == JsonValueKind.Number)
        {
            return element.TryGetDecimal(out value);
        }

        var text = element.GetScalarString();
        if (string.IsNullOrWhiteSpace(text))
        {
            return false;
        }

        text = text.Trim().Replace("%", string.Empty, StringComparison.Ordinal).Replace(",", string.Empty, StringComparison.Ordinal);
        return decimal.TryParse(text, NumberStyles.Any, CultureInfo.InvariantCulture, out value);
    }

    public static bool TryGetInt64Value(this JsonElement element, out long value)
    {
        value = 0;
        if (element.ValueKind == JsonValueKind.Number)
        {
            return element.TryGetInt64(out value);
        }

        if (element.TryGetDecimalValue(out var decimalValue))
        {
            value = decimal.ToInt64(decimal.Truncate(decimalValue));
            return true;
        }

        return false;
    }
}
