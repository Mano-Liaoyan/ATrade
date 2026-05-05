using System.Text.Json;
using System.Text.RegularExpressions;

namespace ATrade.Backtesting;

public static partial class BacktestPersistenceSafety
{
    private const string RedactedSensitiveErrorMessage = "Backtest error details were redacted because they contained sensitive runtime information.";

    private static readonly JsonSerializerOptions SerializerOptions = new(JsonSerializerDefaults.Web)
    {
        PropertyNameCaseInsensitive = true,
    };

    public static string SerializeRequestSnapshot(BacktestRequestSnapshot requestSnapshot)
    {
        var safeSnapshot = NormalizeSafeRequestSnapshot(requestSnapshot);
        return JsonSerializer.Serialize(safeSnapshot, SerializerOptions);
    }

    public static BacktestRequestSnapshot DeserializeRequestSnapshot(string requestJson)
    {
        if (string.IsNullOrWhiteSpace(requestJson))
        {
            throw new BacktestValidationException(BacktestErrorCodes.InvalidPayload, BacktestSafeMessages.InvalidPayload);
        }

        var snapshot = JsonSerializer.Deserialize<BacktestRequestSnapshot>(requestJson, SerializerOptions);
        return NormalizeSafeRequestSnapshot(snapshot);
    }

    public static string? SerializeResult(JsonElement? result)
    {
        if (!result.HasValue)
        {
            return null;
        }

        EnsureNoSensitiveJsonValue(result.Value, "result");
        return result.Value.GetRawText();
    }

    public static JsonElement? DeserializeResult(string? resultJson)
    {
        if (string.IsNullOrWhiteSpace(resultJson))
        {
            return null;
        }

        using var document = JsonDocument.Parse(resultJson);
        var result = document.RootElement.Clone();
        EnsureNoSensitiveJsonValue(result, "result");
        return result;
    }

    public static BacktestError? NormalizeSafeError(BacktestError? error)
    {
        if (error is null)
        {
            return null;
        }

        var code = string.IsNullOrWhiteSpace(error.Code)
            ? BacktestErrorCodes.InvalidPayload
            : error.Code.Trim();
        var message = string.IsNullOrWhiteSpace(error.Message)
            ? "Backtest request failed."
            : error.Message.Trim();

        if (ContainsSensitiveText(code) || ContainsSensitiveText(message))
        {
            message = RedactedSensitiveErrorMessage;
        }

        return new BacktestError(code, message);
    }

    public static BacktestRequestSnapshot NormalizeSafeRequestSnapshot(BacktestRequestSnapshot? requestSnapshot)
    {
        if (requestSnapshot is null)
        {
            throw new BacktestValidationException(BacktestErrorCodes.InvalidPayload, BacktestSafeMessages.InvalidPayload);
        }

        var parameters = requestSnapshot.Parameters ?? new Dictionary<string, JsonElement>(StringComparer.Ordinal);
        foreach (var parameter in parameters)
        {
            EnsureNoSensitiveJsonValue(parameter.Value, parameter.Key);
        }

        var equivalentRequest = new BacktestCreateRequest(
            Symbol: requestSnapshot.Symbol,
            SymbolCode: requestSnapshot.Symbol?.Symbol,
            StrategyId: requestSnapshot.StrategyId,
            Parameters: parameters.ToDictionary(
                parameter => parameter.Key,
                parameter => parameter.Value.Clone(),
                StringComparer.Ordinal),
            ChartRange: requestSnapshot.ChartRange,
            CostModel: requestSnapshot.CostModel is null
                ? null
                : new BacktestCostModel(
                    requestSnapshot.CostModel.CommissionPerTrade,
                    requestSnapshot.CostModel.CommissionBps,
                    requestSnapshot.CostModel.Currency),
            SlippageBps: requestSnapshot.SlippageBps,
            BenchmarkMode: requestSnapshot.BenchmarkMode);

        return BacktestRequestValidator.Validate(equivalentRequest);
    }

    private static void EnsureNoSensitiveJsonValue(JsonElement value, string path)
    {
        switch (value.ValueKind)
        {
            case JsonValueKind.Object:
                foreach (var property in value.EnumerateObject())
                {
                    EnsureSafeJsonPropertyName(property.Name);
                    EnsureNoSensitiveJsonValue(property.Value, $"{path}.{property.Name}");
                }

                break;
            case JsonValueKind.Array:
                var index = 0;
                foreach (var item in value.EnumerateArray())
                {
                    EnsureNoSensitiveJsonValue(item, $"{path}[{index}]");
                    index++;
                }

                break;
            case JsonValueKind.String:
                var text = value.GetString();
                if (ContainsUrlOrAccountIdentifier(text))
                {
                    throw new BacktestValidationException(
                        BacktestErrorCodes.ForbiddenField,
                        BacktestSafeMessages.OrderRoutingNotAllowed,
                        path);
                }

                break;
            case JsonValueKind.Number:
            case JsonValueKind.True:
            case JsonValueKind.False:
            case JsonValueKind.Null:
            case JsonValueKind.Undefined:
                break;
        }
    }

    private static void EnsureSafeJsonPropertyName(string propertyName)
    {
        using var document = JsonDocument.Parse("null");
        var probe = new BacktestCreateRequest(
            Symbol: null,
            SymbolCode: null,
            StrategyId: null,
            Parameters: null,
            ChartRange: null,
            CostModel: null,
            SlippageBps: null,
            BenchmarkMode: null)
        {
            AdditionalProperties = new Dictionary<string, JsonElement>
            {
                [propertyName] = document.RootElement.Clone(),
            },
        };

        try
        {
            BacktestRequestValidator.Validate(probe);
        }
        catch (BacktestValidationException exception) when (exception.Code == BacktestErrorCodes.InvalidSymbol)
        {
            return;
        }
    }

    private static bool ContainsSensitiveText(string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return false;
        }

        return ContainsUrlOrAccountIdentifier(value) ||
               value.Contains("credential", StringComparison.OrdinalIgnoreCase) ||
               value.Contains("password", StringComparison.OrdinalIgnoreCase) ||
               value.Contains("secret", StringComparison.OrdinalIgnoreCase) ||
               value.Contains("token", StringComparison.OrdinalIgnoreCase) ||
               value.Contains("cookie", StringComparison.OrdinalIgnoreCase) ||
               value.Contains("session", StringComparison.OrdinalIgnoreCase) ||
               value.Contains("gateway", StringComparison.OrdinalIgnoreCase) ||
               value.Contains("account", StringComparison.OrdinalIgnoreCase);
    }

    private static bool ContainsUrlOrAccountIdentifier(string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return false;
        }

        return HttpUrlRegex().IsMatch(value) || IbkrAccountIdentifierRegex().IsMatch(value);
    }

    [GeneratedRegex(@"https?://", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    private static partial Regex HttpUrlRegex();

    [GeneratedRegex(@"\bDU\d{4,}\b", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    private static partial Regex IbkrAccountIdentifierRegex();
}
