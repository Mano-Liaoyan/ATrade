using System.Text.RegularExpressions;

namespace ATrade.Brokers.Ibkr;

public static class IbkrGatewayDiagnostics
{
    public static string RedactConfiguredValues(string? message, IbkrGatewayOptions options)
    {
        ArgumentNullException.ThrowIfNull(options);

        if (string.IsNullOrWhiteSpace(message))
        {
            return string.Empty;
        }

        var redactedMessage = message;
        foreach (var value in EnumerateSensitiveConfiguredValues(options).Distinct(StringComparer.OrdinalIgnoreCase))
        {
            redactedMessage = redactedMessage.Replace(value, "[redacted]", StringComparison.OrdinalIgnoreCase);
        }

        redactedMessage = Regex.Replace(redactedMessage, @"(?i)(set-cookie\s*:\s*)[^\r\n<]+", "$1[redacted]");
        return Regex.Replace(
            redactedMessage,
            @"(?i)\b(password|passwd|pwd|token|session|sessionid|cookie|authorization|api[_-]?key)\b(\s*[:=]\s*)['""']?[^'""'\s<>&;]+",
            "$1$2[redacted]");
    }

    private static IEnumerable<string> EnumerateSensitiveConfiguredValues(IbkrGatewayOptions options)
    {
        if (!string.IsNullOrWhiteSpace(options.Username))
        {
            yield return options.Username;
        }

        if (!string.IsNullOrWhiteSpace(options.Password))
        {
            yield return options.Password;
        }

        if (!string.IsNullOrWhiteSpace(options.PaperAccountId))
        {
            yield return options.PaperAccountId;
        }

        if (options.GatewayBaseUrl is not null)
        {
            yield return options.GatewayBaseUrl.ToString();
            yield return options.GatewayBaseUrl.GetLeftPart(UriPartial.Authority);

            if (!string.IsNullOrWhiteSpace(options.GatewayBaseUrl.Host))
            {
                yield return options.GatewayBaseUrl.Host;
            }

            if (!string.IsNullOrWhiteSpace(options.GatewayBaseUrl.UserInfo))
            {
                yield return options.GatewayBaseUrl.UserInfo;
            }
        }
    }
}
