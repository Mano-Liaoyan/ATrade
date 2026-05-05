using System.Text.RegularExpressions;

namespace ATrade.Accounts;

public static partial class PaperCapitalRedaction
{
    public static IbkrPaperCapitalAvailability Redact(IbkrPaperCapitalAvailability availability)
    {
        var messages = availability.Messages
            .Select(message => new PaperCapitalMessage(
                RedactText(message.Code),
                RedactText(message.Message),
                message.Severity))
            .ToArray();

        return availability with { Messages = messages };
    }

    public static string RedactText(string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return string.Empty;
        }

        var redacted = UrlRegex().Replace(value, "[redacted-url]");
        redacted = AccountIdRegex().Replace(redacted, "[redacted-account]");
        redacted = SensitivePairRegex().Replace(redacted, match => $"{match.Groups[1].Value}[redacted]");
        return redacted;
    }

    [GeneratedRegex(@"https?://[^\s,;]+", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    private static partial Regex UrlRegex();

    [GeneratedRegex(@"\b(?:DU|U)\d{4,}\b", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    private static partial Regex AccountIdRegex();

    [GeneratedRegex(@"\b(password|secret|token|cookie|session|credential)\s*[:=]\s*[^\s,;]+", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    private static partial Regex SensitivePairRegex();
}
