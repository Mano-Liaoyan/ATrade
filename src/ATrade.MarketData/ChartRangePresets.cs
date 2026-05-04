namespace ATrade.MarketData;

public static class ChartRangePresets
{
    public const string OneMinute = "1min";
    public const string FiveMinutes = "5mins";
    public const string OneHour = "1h";
    public const string SixHours = "6h";
    public const string OneDay = "1D";
    public const string OneMonth = "1m";
    public const string SixMonths = "6m";
    public const string OneYear = "1y";
    public const string FiveYears = "5y";
    public const string All = "all";

    public const string Default = OneDay;

    private static readonly IReadOnlyDictionary<string, ChartRangePreset> PresetsByValue =
        new Dictionary<string, ChartRangePreset>(StringComparer.OrdinalIgnoreCase)
        {
            [OneMinute] = ChartRangePreset.Minutes(OneMinute, "1min", providerPeriod: "1d", providerBarSize: "1min", minutes: 1),
            [FiveMinutes] = ChartRangePreset.Minutes(FiveMinutes, "5mins", providerPeriod: "1d", providerBarSize: "1min", minutes: 5),
            [OneHour] = ChartRangePreset.Hours(OneHour, "1h", providerPeriod: "1d", providerBarSize: "1min", hours: 1),
            [SixHours] = ChartRangePreset.Hours(SixHours, "6h", providerPeriod: "1d", providerBarSize: "5min", hours: 6),
            [OneDay] = ChartRangePreset.Days(OneDay, "1D", providerPeriod: "2d", providerBarSize: "5min", days: 1),
            [OneMonth] = ChartRangePreset.Months(OneMonth, "1m", providerPeriod: "1m", providerBarSize: "1d", months: 1),
            [SixMonths] = ChartRangePreset.Months(SixMonths, "6m", providerPeriod: "6m", providerBarSize: "1d", months: 6),
            [OneYear] = ChartRangePreset.Years(OneYear, "1y", providerPeriod: "1y", providerBarSize: "1d", years: 1),
            [FiveYears] = ChartRangePreset.Years(FiveYears, "5y", providerPeriod: "5y", providerBarSize: "1w", years: 5),
            [All] = ChartRangePreset.AllTime(All, "All time", providerPeriod: "10y", providerBarSize: "1w"),
        };

    public static IReadOnlyList<ChartRangePreset> AllPresets { get; } = new[]
    {
        PresetsByValue[OneMinute],
        PresetsByValue[FiveMinutes],
        PresetsByValue[OneHour],
        PresetsByValue[SixHours],
        PresetsByValue[OneDay],
        PresetsByValue[OneMonth],
        PresetsByValue[SixMonths],
        PresetsByValue[OneYear],
        PresetsByValue[FiveYears],
        PresetsByValue[All],
    };

    public static IReadOnlyList<string> Supported { get; } = AllPresets.Select(preset => preset.Value).ToArray();

    public static string SupportedValuesMessage => string.Join(", ", Supported);

    public static bool TryGetPreset(string? requestedRange, out ChartRangePreset preset)
    {
        var normalized = string.IsNullOrWhiteSpace(requestedRange) ? Default : requestedRange.Trim();
        return PresetsByValue.TryGetValue(normalized, out preset!);
    }

    public static bool TryNormalize(string? requestedRange, out string normalizedRange)
    {
        if (TryGetPreset(requestedRange, out var preset))
        {
            normalizedRange = preset.Value;
            return true;
        }

        normalizedRange = string.Empty;
        return false;
    }

    public static MarketDataError CreateUnsupportedRangeError(string? requestedRange)
    {
        var range = string.IsNullOrWhiteSpace(requestedRange) ? "<empty>" : requestedRange.Trim();
        return new MarketDataError(
            MarketDataProviderErrorCodes.UnsupportedChartRange,
            $"Chart range '{range}' is not supported. Supported values: {SupportedValuesMessage}.");
    }
}

public sealed record ChartRangePreset(
    string Value,
    string DisplayLabel,
    string ProviderPeriod,
    string ProviderBarSize,
    ChartRangeLookback? Lookback)
{
    public bool IsAllTime => Lookback is null;

    public DateTimeOffset? GetLookbackStartUtc(DateTimeOffset nowUtc)
    {
        if (Lookback is null)
        {
            return null;
        }

        var utcNow = nowUtc.ToUniversalTime();
        return Lookback.Unit switch
        {
            ChartRangeLookbackUnit.Minute => utcNow.AddMinutes(-Lookback.Amount),
            ChartRangeLookbackUnit.Hour => utcNow.AddHours(-Lookback.Amount),
            ChartRangeLookbackUnit.Day => utcNow.AddDays(-Lookback.Amount),
            ChartRangeLookbackUnit.Month => utcNow.AddMonths(-Lookback.Amount),
            ChartRangeLookbackUnit.Year => utcNow.AddYears(-Lookback.Amount),
            _ => throw new InvalidOperationException($"Unsupported chart range lookback unit '{Lookback.Unit}'."),
        };
    }

    public static ChartRangePreset Minutes(string value, string displayLabel, string providerPeriod, string providerBarSize, int minutes) =>
        new(value, displayLabel, providerPeriod, providerBarSize, new ChartRangeLookback(minutes, ChartRangeLookbackUnit.Minute));

    public static ChartRangePreset Hours(string value, string displayLabel, string providerPeriod, string providerBarSize, int hours) =>
        new(value, displayLabel, providerPeriod, providerBarSize, new ChartRangeLookback(hours, ChartRangeLookbackUnit.Hour));

    public static ChartRangePreset Days(string value, string displayLabel, string providerPeriod, string providerBarSize, int days) =>
        new(value, displayLabel, providerPeriod, providerBarSize, new ChartRangeLookback(days, ChartRangeLookbackUnit.Day));

    public static ChartRangePreset Months(string value, string displayLabel, string providerPeriod, string providerBarSize, int months) =>
        new(value, displayLabel, providerPeriod, providerBarSize, new ChartRangeLookback(months, ChartRangeLookbackUnit.Month));

    public static ChartRangePreset Years(string value, string displayLabel, string providerPeriod, string providerBarSize, int years) =>
        new(value, displayLabel, providerPeriod, providerBarSize, new ChartRangeLookback(years, ChartRangeLookbackUnit.Year));

    public static ChartRangePreset AllTime(string value, string displayLabel, string providerPeriod, string providerBarSize) =>
        new(value, displayLabel, providerPeriod, providerBarSize, Lookback: null);
}

public sealed record ChartRangeLookback(int Amount, ChartRangeLookbackUnit Unit);

public enum ChartRangeLookbackUnit
{
    Minute,
    Hour,
    Day,
    Month,
    Year,
}
