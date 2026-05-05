using System.Globalization;
using System.Net.Http.Json;
using System.Text.Json;

namespace ATrade.Brokers.Ibkr;

public sealed class IbkrAccountSummaryClient(
    HttpClient httpClient,
    IbkrGatewayOptions gatewayOptions,
    IIbkrPaperTradingGuard paperTradingGuard) : IIbkrAccountSummaryClient
{
    public const string AccountSummaryPathTemplate = "/v1/api/portfolio/{0}/summary";

    private static readonly string[] PreferredBalanceMetrics =
    [
        "totalcashvalue",
        "totalCashValue",
        "TotalCashValue",
        "netliquidation",
        "netLiquidation",
        "NetLiquidation",
    ];

    public async Task<IbkrAccountSummaryBalance> GetConfiguredPaperAccountBalanceAsync(CancellationToken cancellationToken = default)
    {
        paperTradingGuard.EnsurePaperOnly();

        if (!gatewayOptions.HasConfiguredPaperAccountId || string.IsNullOrWhiteSpace(gatewayOptions.PaperAccountId))
        {
            throw new InvalidOperationException("IBKR paper account id is not configured.");
        }

        var path = string.Format(
            CultureInfo.InvariantCulture,
            AccountSummaryPathTemplate,
            Uri.EscapeDataString(gatewayOptions.PaperAccountId.Trim()));

        using var response = await httpClient.GetAsync(path, cancellationToken).ConfigureAwait(false);
        response.EnsureSuccessStatusCode();

        await using var stream = await response.Content.ReadAsStreamAsync(cancellationToken).ConfigureAwait(false);
        using var document = await JsonDocument.ParseAsync(stream, cancellationToken: cancellationToken).ConfigureAwait(false);
        if (TryReadBalance(document.RootElement, out var balance))
        {
            return balance;
        }

        throw new InvalidOperationException("IBKR account summary did not include a cash or net liquidation balance.");
    }

    internal static bool TryReadBalance(JsonElement root, out IbkrAccountSummaryBalance balance)
    {
        if (root.ValueKind == JsonValueKind.Object)
        {
            foreach (var metric in PreferredBalanceMetrics)
            {
                if (TryGetPropertyIgnoreCase(root, metric, out var metricElement) &&
                    TryReadMetric(metricElement, metric, out balance))
                {
                    return true;
                }
            }
        }

        if (root.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in root.EnumerateArray())
            {
                if (TryReadBalance(item, out balance))
                {
                    return true;
                }
            }
        }

        balance = default!;
        return false;
    }

    private static bool TryReadMetric(JsonElement element, string metric, out IbkrAccountSummaryBalance balance)
    {
        if (TryReadDecimal(element, out var amount))
        {
            balance = new IbkrAccountSummaryBalance(amount, LocalPaperCapitalCurrency.DefaultCurrency, NormalizeMetric(metric));
            return true;
        }

        if (element.ValueKind == JsonValueKind.Object)
        {
            var currency = TryGetPropertyIgnoreCase(element, "currency", out var currencyElement) && TryReadString(currencyElement, out var currencyValue)
                ? NormalizeCurrency(currencyValue)
                : LocalPaperCapitalCurrency.DefaultCurrency;

            foreach (var amountProperty in new[] { "amount", "value", "current", "balance" })
            {
                if (TryGetPropertyIgnoreCase(element, amountProperty, out var amountElement) &&
                    TryReadDecimal(amountElement, out amount))
                {
                    balance = new IbkrAccountSummaryBalance(amount, currency, NormalizeMetric(metric));
                    return true;
                }
            }
        }

        balance = default!;
        return false;
    }

    private static bool TryGetPropertyIgnoreCase(JsonElement element, string propertyName, out JsonElement property)
    {
        if (element.ValueKind != JsonValueKind.Object)
        {
            property = default;
            return false;
        }

        foreach (var candidate in element.EnumerateObject())
        {
            if (string.Equals(candidate.Name, propertyName, StringComparison.OrdinalIgnoreCase))
            {
                property = candidate.Value;
                return true;
            }
        }

        property = default;
        return false;
    }

    private static bool TryReadDecimal(JsonElement element, out decimal value)
    {
        switch (element.ValueKind)
        {
            case JsonValueKind.Number:
                return element.TryGetDecimal(out value);
            case JsonValueKind.String:
                return decimal.TryParse(element.GetString(), NumberStyles.Number, CultureInfo.InvariantCulture, out value);
            default:
                value = default;
                return false;
        }
    }

    private static bool TryReadString(JsonElement element, out string value)
    {
        if (element.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(element.GetString()))
        {
            value = element.GetString()!.Trim();
            return true;
        }

        value = string.Empty;
        return false;
    }

    private static string NormalizeMetric(string metric) =>
        string.Equals(metric, "totalcashvalue", StringComparison.OrdinalIgnoreCase)
            ? "totalcashvalue"
            : "netliquidation";

    private static string NormalizeCurrency(string currency) => currency.Trim().ToUpperInvariant();

    private static class LocalPaperCapitalCurrency
    {
        public const string DefaultCurrency = "USD";
    }
}
