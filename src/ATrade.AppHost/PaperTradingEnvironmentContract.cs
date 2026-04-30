using ATrade.Brokers.Ibkr;

namespace ATrade.AppHost;

public sealed record PaperTradingEnvironmentContract(
    string BrokerIntegrationEnabled,
    string BrokerAccountMode,
    string GatewayUrl,
    string GatewayPort,
    string GatewayImage,
    string PaperAccountId,
    string IbkrUsername,
    string IbkrPassword,
    string? GatewayTimeoutSeconds)
{
    public bool IsBrokerIntegrationEnabled =>
        bool.TryParse(BrokerIntegrationEnabled, out var enabled) && enabled;

    public bool HasConfiguredIbeamCredentials =>
        HasRealCredentialValue(IbkrUsername, IbkrGatewayPlaceholderValues.Username) &&
        HasRealCredentialValue(IbkrPassword, IbkrGatewayPlaceholderValues.Password);

    public bool ShouldStartIbeamContainer =>
        IsBrokerIntegrationEnabled &&
        HasConfiguredGatewayImage &&
        HasConfiguredIbeamCredentials;

    public bool HasConfiguredGatewayImage =>
        !string.IsNullOrWhiteSpace(GatewayImage) &&
        !GatewayImage.Contains("example.invalid", StringComparison.OrdinalIgnoreCase);

    public int GetGatewayPort()
    {
        if (int.TryParse(GatewayPort, out var port) && port is > 0 and <= 65535)
        {
            return port;
        }

        throw new InvalidOperationException($"{IbkrGatewayEnvironmentVariables.GatewayPort} must be a valid TCP port, but was '{GatewayPort}'.");
    }

    public bool TryGetGatewayImageReference(out string image, out string tag)
    {
        image = string.Empty;
        tag = string.Empty;

        if (!ShouldStartIbeamContainer)
        {
            return false;
        }

        var lastSlash = GatewayImage.LastIndexOf('/');
        var lastColon = GatewayImage.LastIndexOf(':');

        if (lastColon > lastSlash)
        {
            image = GatewayImage[..lastColon];
            tag = GatewayImage[(lastColon + 1)..];
            return true;
        }

        image = GatewayImage;
        tag = "latest";
        return true;
    }

    public static PaperTradingEnvironmentContract Load(string contractPath)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(contractPath);

        var values = LoadMergedContractValues(contractPath);

        return new PaperTradingEnvironmentContract(
            BrokerIntegrationEnabled: ResolveRequiredValue(values, IbkrGatewayEnvironmentVariables.IntegrationEnabled, contractPath),
            BrokerAccountMode: ResolveRequiredValue(values, IbkrGatewayEnvironmentVariables.AccountMode, contractPath),
            GatewayUrl: ResolveRequiredValue(values, IbkrGatewayEnvironmentVariables.GatewayUrl, contractPath),
            GatewayPort: ResolveRequiredValue(values, IbkrGatewayEnvironmentVariables.GatewayPort, contractPath),
            GatewayImage: ResolveRequiredValue(values, IbkrGatewayEnvironmentVariables.GatewayImage, contractPath),
            PaperAccountId: ResolveRequiredValue(values, IbkrGatewayEnvironmentVariables.PaperAccountId, contractPath),
            IbkrUsername: ResolveOptionalValue(values, IbkrGatewayEnvironmentVariables.Username) ?? string.Empty,
            IbkrPassword: ResolveOptionalValue(values, IbkrGatewayEnvironmentVariables.Password) ?? string.Empty,
            GatewayTimeoutSeconds: ResolveOptionalValue(values, IbkrGatewayEnvironmentVariables.GatewayTimeoutSeconds));
    }

    private static bool HasRealCredentialValue(string? value, string fakePlaceholder)
    {
        return !string.IsNullOrWhiteSpace(value) &&
            !string.Equals(value.Trim(), fakePlaceholder, StringComparison.OrdinalIgnoreCase);
    }

    private static Dictionary<string, string> LoadMergedContractValues(string contractPath)
    {
        var contractDirectory = Path.GetDirectoryName(contractPath)
            ?? throw new InvalidOperationException($"Failed to resolve the local paper-trading contract directory for '{contractPath}'.");
        var templatePath = Path.Combine(contractDirectory, ".env.template");
        var values = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        if (File.Exists(templatePath) &&
            !Path.GetFullPath(templatePath).Equals(Path.GetFullPath(contractPath), StringComparison.OrdinalIgnoreCase))
        {
            Overlay(values, ParseEnvironmentFile(templatePath));
        }

        Overlay(values, ParseEnvironmentFile(contractPath));
        return values;
    }

    private static void Overlay(IDictionary<string, string> destination, IReadOnlyDictionary<string, string> source)
    {
        foreach (var pair in source)
        {
            destination[pair.Key] = pair.Value;
        }
    }

    private static Dictionary<string, string> ParseEnvironmentFile(string path)
    {
        if (!File.Exists(path))
        {
            throw new InvalidOperationException($"Failed to load the local paper-trading contract file at '{path}'.");
        }

        var values = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        foreach (var rawLine in File.ReadAllLines(path))
        {
            var line = rawLine.Trim();
            if (string.IsNullOrWhiteSpace(line) || line.StartsWith('#'))
            {
                continue;
            }

            var separatorIndex = line.IndexOf('=');
            if (separatorIndex <= 0)
            {
                continue;
            }

            var key = line[..separatorIndex].Trim();
            var value = line[(separatorIndex + 1)..].Trim().Trim('"', '\'');
            values[key] = value;
        }

        return values;
    }

    private static string ResolveRequiredValue(IReadOnlyDictionary<string, string> values, string key, string contractPath)
    {
        var value = ResolveOptionalValue(values, key);
        if (!string.IsNullOrWhiteSpace(value))
        {
            return value;
        }

        throw new InvalidOperationException($"{key} must be provided through the environment or the local paper-trading contract at '{contractPath}'.");
    }

    private static string? ResolveOptionalValue(IReadOnlyDictionary<string, string> values, string key)
    {
        var environmentValue = Environment.GetEnvironmentVariable(key);
        if (!string.IsNullOrWhiteSpace(environmentValue))
        {
            return environmentValue;
        }

        return values.TryGetValue(key, out var fileValue) && !string.IsNullOrWhiteSpace(fileValue)
            ? fileValue
            : null;
    }
}
