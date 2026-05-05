using System.Text.Json;
using ATrade.Accounts;
using ATrade.MarketData;

namespace ATrade.Backtesting;

public sealed class BacktestValidationException : ArgumentException
{
    public BacktestValidationException(string code, string message, string? paramName = null)
        : base(message, paramName)
    {
        Code = code;
    }

    public string Code { get; }
}

public static class BacktestRequestValidator
{
    private static readonly HashSet<string> MultiSymbolFieldNames = new(StringComparer.OrdinalIgnoreCase)
    {
        "symbols",
        "symbolCodes",
        "portfolio",
        "basket",
        "legs",
    };

    private static readonly HashSet<string> DirectBarFieldNames = new(StringComparer.OrdinalIgnoreCase)
    {
        "bars",
        "barSeries",
        "candles",
        "ohlcv",
        "ohlcvBars",
        "prices",
        "priceSeries",
        "marketDataBars",
        "historicalBars",
        "data",
    };

    private static readonly HashSet<string> CustomCodeFieldNames = new(StringComparer.OrdinalIgnoreCase)
    {
        "code",
        "sourceCode",
        "script",
        "customStrategy",
        "strategyCode",
        "algorithm",
        "algorithmCode",
        "leanWorkspace",
        "workspacePath",
        "python",
        "csharp",
    };

    private static readonly HashSet<string> OrderRoutingFieldNames = new(StringComparer.OrdinalIgnoreCase)
    {
        "account",
        "accountId",
        "accountIdentifier",
        "brokerAccount",
        "credential",
        "credentials",
        "password",
        "secret",
        "token",
        "cookie",
        "session",
        "gateway",
        "gatewayUrl",
        "url",
        "order",
        "orders",
        "orderRoute",
        "orderRouting",
        "orderType",
        "route",
        "routing",
        "broker",
        "execution",
        "trade",
        "trades",
        "buy",
        "sell",
        "side",
        "quantity",
        "qty",
        "timeInForce",
    };

    public static BacktestRequestSnapshot Validate(BacktestCreateRequest? request)
    {
        if (request is null)
        {
            throw new BacktestValidationException(BacktestErrorCodes.InvalidPayload, BacktestSafeMessages.InvalidPayload);
        }

        RejectForbiddenProperties(request.AdditionalProperties);

        var symbol = NormalizeSymbol(request.Symbol, request.SymbolCode);
        var strategyId = NormalizeStrategy(request.StrategyId);
        var parameters = NormalizeParameters(request.Parameters);
        var chartRange = NormalizeChartRange(request.ChartRange);
        var costModel = NormalizeCostModel(request.CostModel);
        var slippageBps = NormalizeSlippage(request.SlippageBps);
        var benchmarkMode = NormalizeBenchmarkMode(request.BenchmarkMode);
        var engineId = NormalizeEngineId(request.EngineId);

        return new BacktestRequestSnapshot(
            symbol,
            strategyId,
            parameters,
            chartRange,
            costModel,
            slippageBps,
            benchmarkMode,
            engineId);
    }

    private static MarketDataSymbolIdentity NormalizeSymbol(MarketDataSymbolIdentity? symbol, string? symbolCode)
    {
        if (symbol is null && string.IsNullOrWhiteSpace(symbolCode))
        {
            throw new BacktestValidationException(BacktestErrorCodes.InvalidSymbol, BacktestSafeMessages.InvalidSymbol, nameof(symbolCode));
        }

        MarketDataSymbolIdentity normalized;
        try
        {
            normalized = symbol is not null
                ? MarketDataSymbolIdentity.Create(
                    symbol.Symbol,
                    symbol.Provider,
                    symbol.ProviderSymbolId,
                    symbol.AssetClass,
                    symbol.Exchange,
                    symbol.Currency)
                : MarketDataSymbolIdentity.Create(
                    symbolCode!,
                    ExactInstrumentIdentityProviders.Manual,
                    providerSymbolId: null,
                    MarketDataAssetClasses.Stock,
                    exchange: "UNKNOWN",
                    currency: BacktestDefaults.Currency);
        }
        catch (ArgumentException exception)
        {
            throw new BacktestValidationException(BacktestErrorCodes.InvalidSymbol, exception.Message, nameof(symbolCode));
        }

        if (!string.Equals(normalized.AssetClass, MarketDataAssetClasses.Stock, StringComparison.OrdinalIgnoreCase))
        {
            throw new BacktestValidationException(BacktestErrorCodes.UnsupportedScope, BacktestSafeMessages.UnsupportedScope, nameof(symbol.AssetClass));
        }

        if (!string.IsNullOrWhiteSpace(symbolCode) &&
            ExactInstrumentIdentity.TryNormalizeSymbol(symbolCode, out var normalizedSymbolCode, out _) &&
            !string.Equals(normalized.Symbol, normalizedSymbolCode, StringComparison.OrdinalIgnoreCase))
        {
            throw new BacktestValidationException(BacktestErrorCodes.UnsupportedScope, BacktestSafeMessages.UnsupportedScope, nameof(symbolCode));
        }

        return normalized;
    }

    private static string NormalizeStrategy(string? strategyId)
    {
        if (!BacktestStrategyIds.TryNormalize(strategyId, out var normalizedStrategyId))
        {
            throw new BacktestValidationException(
                BacktestErrorCodes.UnsupportedStrategy,
                $"{BacktestSafeMessages.UnsupportedStrategy} Supported values: {BacktestStrategyIds.SupportedValuesMessage}.",
                nameof(strategyId));
        }

        return normalizedStrategyId;
    }

    private static IReadOnlyDictionary<string, JsonElement> NormalizeParameters(IDictionary<string, JsonElement>? parameters)
    {
        if (parameters is null || parameters.Count == 0)
        {
            return new Dictionary<string, JsonElement>(StringComparer.Ordinal);
        }

        if (parameters.Count > BacktestValidationLimits.MaximumParameterCount)
        {
            throw new BacktestValidationException(
                BacktestErrorCodes.InvalidParameters,
                $"Backtest parameter bags may contain at most {BacktestValidationLimits.MaximumParameterCount} keys.",
                nameof(parameters));
        }

        var normalized = new Dictionary<string, JsonElement>(StringComparer.Ordinal);
        foreach (var parameter in parameters)
        {
            var key = parameter.Key?.Trim();
            if (string.IsNullOrWhiteSpace(key))
            {
                throw new BacktestValidationException(BacktestErrorCodes.InvalidParameters, "Backtest parameter names are required.", nameof(parameters));
            }

            if (key.Length > BacktestValidationLimits.MaximumParameterNameLength)
            {
                throw new BacktestValidationException(
                    BacktestErrorCodes.InvalidParameters,
                    $"Backtest parameter names must be {BacktestValidationLimits.MaximumParameterNameLength} characters or fewer.",
                    nameof(parameters));
            }

            RejectForbiddenPropertyName(key);
            ValidateParameterValue(key, parameter.Value, depth: 0);
            normalized[key] = parameter.Value.Clone();
        }

        return normalized;
    }

    private static string NormalizeChartRange(string? chartRange)
    {
        if (ChartRangePresets.TryNormalize(chartRange, out var normalizedRange))
        {
            return normalizedRange;
        }

        throw new BacktestValidationException(
            BacktestErrorCodes.UnsupportedChartRange,
            ChartRangePresets.CreateUnsupportedRangeError(chartRange).Message,
            nameof(chartRange));
    }

    private static BacktestCostModelSnapshot NormalizeCostModel(BacktestCostModel? costModel)
    {
        if (costModel is null)
        {
            return new BacktestCostModelSnapshot(
                BacktestDefaults.DefaultCommissionPerTrade,
                BacktestDefaults.DefaultCommissionBps,
                BacktestDefaults.Currency);
        }

        RejectForbiddenProperties(costModel.AdditionalProperties);
        var commissionPerTrade = NormalizeBoundedDecimal(
            costModel.CommissionPerTrade ?? BacktestDefaults.DefaultCommissionPerTrade,
            BacktestValidationLimits.MaximumCommissionPerTrade,
            BacktestErrorCodes.InvalidCostModel,
            "Commission per trade must be between 0 and the supported maximum.",
            nameof(costModel.CommissionPerTrade));
        var commissionBps = NormalizeBoundedDecimal(
            costModel.CommissionBps ?? BacktestDefaults.DefaultCommissionBps,
            BacktestValidationLimits.MaximumCommissionBps,
            BacktestErrorCodes.InvalidCostModel,
            "Commission bps must be between 0 and the supported maximum.",
            nameof(costModel.CommissionBps));
        string currency;
        try
        {
            currency = LocalPaperCapitalValidator.NormalizeCurrency(costModel.Currency);
        }
        catch (PaperCapitalValidationException exception)
        {
            throw new BacktestValidationException(BacktestErrorCodes.InvalidCostModel, exception.Message, nameof(costModel.Currency));
        }

        return new BacktestCostModelSnapshot(commissionPerTrade, commissionBps, currency);
    }

    private static decimal NormalizeSlippage(decimal? slippageBps) => NormalizeBoundedDecimal(
        slippageBps ?? BacktestDefaults.DefaultSlippageBps,
        BacktestValidationLimits.MaximumSlippageBps,
        BacktestErrorCodes.InvalidSlippage,
        "Slippage bps must be between 0 and the supported maximum.",
        nameof(slippageBps));

    private static decimal NormalizeBoundedDecimal(
        decimal value,
        decimal maximum,
        string errorCode,
        string message,
        string paramName)
    {
        if (value < 0 || value > maximum)
        {
            throw new BacktestValidationException(errorCode, message, paramName);
        }

        return decimal.Round(value, 4, MidpointRounding.AwayFromZero);
    }

    private static string? NormalizeEngineId(string? engineId)
    {
        if (string.IsNullOrWhiteSpace(engineId))
        {
            return null;
        }

        var normalized = engineId.Trim().ToLowerInvariant();
        if (normalized.Length > BacktestValidationLimits.MaximumParameterNameLength ||
            normalized.Any(character => !(char.IsAsciiLetterOrDigit(character) || character is '-' or '_' or '.')))
        {
            throw new BacktestValidationException(
                BacktestErrorCodes.InvalidParameters,
                "Backtest engine ids may contain only letters, numbers, dots, dashes, and underscores.",
                nameof(engineId));
        }

        RejectForbiddenPropertyName(normalized);
        return normalized;
    }

    private static string NormalizeBenchmarkMode(string? benchmarkMode)
    {
        if (BacktestBenchmarkModes.TryNormalize(benchmarkMode, out var normalizedBenchmarkMode))
        {
            return normalizedBenchmarkMode;
        }

        throw new BacktestValidationException(
            BacktestErrorCodes.InvalidBenchmark,
            $"Benchmark mode is not supported. Supported values: {BacktestBenchmarkModes.SupportedValuesMessage}.",
            nameof(benchmarkMode));
    }

    private static void RejectForbiddenProperties(IDictionary<string, JsonElement>? additionalProperties)
    {
        if (additionalProperties is null || additionalProperties.Count == 0)
        {
            return;
        }

        foreach (var propertyName in additionalProperties.Keys)
        {
            RejectForbiddenPropertyName(propertyName);
        }
    }

    private static void ValidateParameterValue(string path, JsonElement value, int depth)
    {
        if (depth > BacktestValidationLimits.MaximumParameterDepth)
        {
            throw new BacktestValidationException(
                BacktestErrorCodes.InvalidParameters,
                $"Backtest parameter '{path}' exceeds the supported JSON depth.",
                nameof(value));
        }

        switch (value.ValueKind)
        {
            case JsonValueKind.Object:
                foreach (var property in value.EnumerateObject())
                {
                    RejectForbiddenPropertyName(property.Name);
                    ValidateParameterValue($"{path}.{property.Name}", property.Value, depth + 1);
                }

                break;
            case JsonValueKind.Array:
                var index = 0;
                foreach (var item in value.EnumerateArray())
                {
                    ValidateParameterValue($"{path}[{index}]", item, depth + 1);
                    index++;
                }

                break;
            case JsonValueKind.String:
                var text = value.GetString();
                if (text is not null && text.Length > BacktestValidationLimits.MaximumParameterStringLength)
                {
                    throw new BacktestValidationException(
                        BacktestErrorCodes.InvalidParameters,
                        $"Backtest parameter '{path}' string values must be {BacktestValidationLimits.MaximumParameterStringLength} characters or fewer.",
                        nameof(value));
                }

                break;
            case JsonValueKind.Number:
            case JsonValueKind.True:
            case JsonValueKind.False:
            case JsonValueKind.Null:
                break;
            default:
                throw new BacktestValidationException(
                    BacktestErrorCodes.InvalidParameters,
                    $"Backtest parameter '{path}' is not a supported JSON value.",
                    nameof(value));
        }
    }

    private static void RejectForbiddenPropertyName(string? propertyName)
    {
        var normalized = propertyName?.Trim();
        if (string.IsNullOrWhiteSpace(normalized))
        {
            return;
        }

        if (MultiSymbolFieldNames.Contains(normalized))
        {
            throw new BacktestValidationException(BacktestErrorCodes.UnsupportedScope, BacktestSafeMessages.UnsupportedScope);
        }

        if (DirectBarFieldNames.Contains(normalized))
        {
            throw new BacktestValidationException(BacktestErrorCodes.ForbiddenField, BacktestSafeMessages.DirectBarsNotAllowed);
        }

        if (CustomCodeFieldNames.Contains(normalized))
        {
            throw new BacktestValidationException(BacktestErrorCodes.ForbiddenField, BacktestSafeMessages.CustomCodeNotAllowed);
        }

        if (OrderRoutingFieldNames.Contains(normalized) || ContainsSensitiveFieldFragment(normalized))
        {
            throw new BacktestValidationException(BacktestErrorCodes.ForbiddenField, BacktestSafeMessages.OrderRoutingNotAllowed);
        }
    }

    private static bool ContainsSensitiveFieldFragment(string propertyName) =>
        propertyName.Contains("account", StringComparison.OrdinalIgnoreCase) ||
        propertyName.Contains("credential", StringComparison.OrdinalIgnoreCase) ||
        propertyName.Contains("password", StringComparison.OrdinalIgnoreCase) ||
        propertyName.Contains("secret", StringComparison.OrdinalIgnoreCase) ||
        propertyName.Contains("token", StringComparison.OrdinalIgnoreCase) ||
        propertyName.Contains("cookie", StringComparison.OrdinalIgnoreCase) ||
        propertyName.Contains("session", StringComparison.OrdinalIgnoreCase) ||
        propertyName.Contains("gateway", StringComparison.OrdinalIgnoreCase) ||
        propertyName.EndsWith("Url", StringComparison.OrdinalIgnoreCase);
}
