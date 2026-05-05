namespace ATrade.Accounts;

public static class PaperCapitalErrorCodes
{
    public const string InvalidPayload = "invalid-paper-capital-payload";
    public const string InvalidAmount = "invalid-paper-capital-amount";
    public const string InvalidCurrency = "invalid-paper-capital-currency";
    public const string StorageUnavailable = "paper-capital-storage-unavailable";
    public const string IbkrDisabled = "ibkr-paper-balance-disabled";
    public const string IbkrCredentialsMissing = "ibkr-paper-balance-credentials-missing";
    public const string IbkrUnauthenticated = "ibkr-paper-balance-unauthenticated";
    public const string IbkrRejectedLive = "ibkr-paper-balance-rejected-live";
    public const string IbkrTimeout = "ibkr-paper-balance-timeout";
    public const string IbkrUnavailable = "ibkr-paper-balance-unavailable";
    public const string LocalUnconfigured = "local-paper-capital-unconfigured";
    public const string NoCapitalSource = "paper-capital-source-unavailable";
}

public static class PaperCapitalSafeMessages
{
    public const string IbkrSourceUnavailable = "IBKR paper balance is not available.";
    public const string IbkrCredentialsMissing = "IBKR paper balance requires a configured paper iBeam session.";
    public const string IbkrUnauthenticated = "IBKR paper balance requires an authenticated paper iBeam session.";
    public const string IbkrRejectedLive = "IBKR paper balance is disabled because only paper mode is supported.";
    public const string IbkrTimeout = "IBKR paper balance read timed out.";
    public const string LocalStorageUnavailable = "Local paper capital storage is unavailable.";
    public const string LocalSourceUnconfigured = "Local paper capital has not been configured.";
    public const string NoCapitalSource = "No paper capital source is configured.";
}

public sealed class PaperCapitalValidationException : ArgumentException
{
    public PaperCapitalValidationException(string code, string message, string? paramName = null)
        : base(message, paramName)
    {
        Code = code;
    }

    public string Code { get; }
}

public sealed record LocalPaperCapitalValue(decimal Amount, string Currency);

public static class LocalPaperCapitalValidator
{
    public const string DefaultCurrency = "USD";

    private static readonly HashSet<string> SupportedCurrencies = new(StringComparer.OrdinalIgnoreCase)
    {
        DefaultCurrency,
    };

    public static LocalPaperCapitalValue Validate(LocalPaperCapitalUpdateRequest? request)
    {
        if (request is null)
        {
            throw new PaperCapitalValidationException(
                PaperCapitalErrorCodes.InvalidPayload,
                "A local paper capital payload is required.");
        }

        RejectSensitiveAdditionalProperties(request);

        if (!request.Amount.HasValue)
        {
            throw new PaperCapitalValidationException(
                PaperCapitalErrorCodes.InvalidAmount,
                "Local paper capital amount is required.",
                nameof(request.Amount));
        }

        if (request.Amount.Value <= 0)
        {
            throw new PaperCapitalValidationException(
                PaperCapitalErrorCodes.InvalidAmount,
                "Local paper capital amount must be greater than zero.",
                nameof(request.Amount));
        }

        var currency = NormalizeCurrency(request.Currency);
        return new LocalPaperCapitalValue(decimal.Round(request.Amount.Value, 2, MidpointRounding.AwayFromZero), currency);
    }

    public static string NormalizeCurrency(string? currency)
    {
        var normalizedCurrency = string.IsNullOrWhiteSpace(currency)
            ? DefaultCurrency
            : currency.Trim().ToUpperInvariant();

        if (!SupportedCurrencies.Contains(normalizedCurrency))
        {
            throw new PaperCapitalValidationException(
                PaperCapitalErrorCodes.InvalidCurrency,
                "Local paper capital currency is not supported.",
                nameof(currency));
        }

        return normalizedCurrency;
    }

    private static void RejectSensitiveAdditionalProperties(LocalPaperCapitalUpdateRequest request)
    {
        if (request.AdditionalProperties is null || request.AdditionalProperties.Count == 0)
        {
            return;
        }

        foreach (var propertyName in request.AdditionalProperties.Keys)
        {
            if (propertyName.Contains("account", StringComparison.OrdinalIgnoreCase) ||
                propertyName.Contains("credential", StringComparison.OrdinalIgnoreCase) ||
                propertyName.Contains("password", StringComparison.OrdinalIgnoreCase) ||
                propertyName.Contains("token", StringComparison.OrdinalIgnoreCase) ||
                propertyName.Contains("cookie", StringComparison.OrdinalIgnoreCase) ||
                propertyName.Contains("session", StringComparison.OrdinalIgnoreCase) ||
                propertyName.Contains("gateway", StringComparison.OrdinalIgnoreCase) ||
                propertyName.Contains("url", StringComparison.OrdinalIgnoreCase))
            {
                throw new PaperCapitalValidationException(
                    PaperCapitalErrorCodes.InvalidPayload,
                    "Local paper capital updates must not include provider account or credential fields.");
            }
        }
    }
}
