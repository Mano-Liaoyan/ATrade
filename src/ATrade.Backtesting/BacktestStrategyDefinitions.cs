using System.Text.Json;

namespace ATrade.Backtesting;

public static class BacktestStrategyParameterTypes
{
    public const string Integer = "integer";
    public const string Decimal = "decimal";
}

public static class BacktestStrategyParameterNames
{
    public const string SmaShortWindow = "shortWindow";
    public const string SmaLongWindow = "longWindow";
    public const string RsiPeriod = "rsiPeriod";
    public const string RsiOversoldThreshold = "oversoldThreshold";
    public const string RsiOverboughtThreshold = "overboughtThreshold";
    public const string BreakoutLookbackWindow = "lookbackWindow";
}

public sealed record BacktestStrategyParameterDefinition(
    string Name,
    string DisplayName,
    string Description,
    string ValueType,
    decimal DefaultValue,
    decimal MinimumValue,
    decimal MaximumValue)
{
    public JsonElement CreateDefaultJsonValue() => ValueType switch
    {
        BacktestStrategyParameterTypes.Integer => JsonSerializer.SerializeToElement((int)DefaultValue),
        _ => JsonSerializer.SerializeToElement(DefaultValue),
    };
}

public sealed record BacktestStrategyDefinition(
    string Id,
    string DisplayName,
    string Description,
    IReadOnlyList<BacktestStrategyParameterDefinition> Parameters)
{
    public IReadOnlyList<string> ParameterNames { get; } = Parameters.Select(parameter => parameter.Name).ToArray();
}

public static class BacktestStrategyCatalog
{
    public static IReadOnlyList<BacktestStrategyDefinition> BuiltIn { get; } =
    [
        new BacktestStrategyDefinition(
            BacktestStrategyIds.SmaCrossover,
            "SMA crossover",
            "Generates long/flat signals when a short simple moving average crosses a longer simple moving average.",
            [
                new BacktestStrategyParameterDefinition(
                    BacktestStrategyParameterNames.SmaShortWindow,
                    "Short SMA window",
                    "Number of bars used for the faster moving average.",
                    BacktestStrategyParameterTypes.Integer,
                    DefaultValue: 20m,
                    MinimumValue: 2m,
                    MaximumValue: 250m),
                new BacktestStrategyParameterDefinition(
                    BacktestStrategyParameterNames.SmaLongWindow,
                    "Long SMA window",
                    "Number of bars used for the slower moving average; must be greater than the short window.",
                    BacktestStrategyParameterTypes.Integer,
                    DefaultValue: 50m,
                    MinimumValue: 3m,
                    MaximumValue: 500m),
            ]),
        new BacktestStrategyDefinition(
            BacktestStrategyIds.RsiMeanReversion,
            "RSI mean reversion",
            "Generates oversold/overbought reversal signals from a relative strength index threshold model.",
            [
                new BacktestStrategyParameterDefinition(
                    BacktestStrategyParameterNames.RsiPeriod,
                    "RSI period",
                    "Number of bars used to calculate RSI.",
                    BacktestStrategyParameterTypes.Integer,
                    DefaultValue: 14m,
                    MinimumValue: 2m,
                    MaximumValue: 100m),
                new BacktestStrategyParameterDefinition(
                    BacktestStrategyParameterNames.RsiOversoldThreshold,
                    "Oversold threshold",
                    "RSI value at or below which the strategy may enter a long position.",
                    BacktestStrategyParameterTypes.Decimal,
                    DefaultValue: 30m,
                    MinimumValue: 1m,
                    MaximumValue: 99m),
                new BacktestStrategyParameterDefinition(
                    BacktestStrategyParameterNames.RsiOverboughtThreshold,
                    "Overbought threshold",
                    "RSI value at or above which the strategy may exit a long position.",
                    BacktestStrategyParameterTypes.Decimal,
                    DefaultValue: 70m,
                    MinimumValue: 1m,
                    MaximumValue: 99m),
            ]),
        new BacktestStrategyDefinition(
            BacktestStrategyIds.Breakout,
            "Breakout",
            "Generates long/flat signals when price closes above or below the prior lookback window.",
            [
                new BacktestStrategyParameterDefinition(
                    BacktestStrategyParameterNames.BreakoutLookbackWindow,
                    "Lookback window",
                    "Number of prior bars used to calculate breakout and breakdown levels.",
                    BacktestStrategyParameterTypes.Integer,
                    DefaultValue: 20m,
                    MinimumValue: 2m,
                    MaximumValue: 250m),
            ]),
    ];

    public static bool TryGetDefinition(string strategyId, out BacktestStrategyDefinition definition)
    {
        definition = BuiltIn.FirstOrDefault(candidate => string.Equals(candidate.Id, strategyId, StringComparison.Ordinal))!;
        return definition is not null;
    }

    public static BacktestStrategyDefinition GetDefinition(string strategyId) =>
        TryGetDefinition(strategyId, out var definition)
            ? definition
            : throw new BacktestValidationException(
                BacktestErrorCodes.UnsupportedStrategy,
                $"{BacktestSafeMessages.UnsupportedStrategy} Supported values: {BacktestStrategyIds.SupportedValuesMessage}.",
                nameof(strategyId));

    public static IReadOnlyDictionary<string, JsonElement> CreateDefaultParameters(string strategyId)
    {
        var definition = GetDefinition(strategyId);
        return definition.Parameters.ToDictionary(
            parameter => parameter.Name,
            parameter => parameter.CreateDefaultJsonValue(),
            StringComparer.Ordinal);
    }
}
