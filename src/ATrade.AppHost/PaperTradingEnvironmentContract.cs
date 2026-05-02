using ATrade.Brokers.Ibkr;
using ATrade.ServiceDefaults;

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

        return Load(LocalRuntimeContractLoader.Load(new LocalRuntimeContractLoadOptions(ContractPath: contractPath)));
    }

    public static PaperTradingEnvironmentContract Load(LocalRuntimeContract runtimeContract)
    {
        ArgumentNullException.ThrowIfNull(runtimeContract);

        var paperTrading = runtimeContract.PaperTrading;
        return new PaperTradingEnvironmentContract(
            BrokerIntegrationEnabled: paperTrading.BrokerIntegrationEnabled,
            BrokerAccountMode: paperTrading.BrokerAccountMode,
            GatewayUrl: paperTrading.GatewayUrl,
            GatewayPort: paperTrading.GatewayPort,
            GatewayImage: paperTrading.GatewayImage,
            PaperAccountId: paperTrading.PaperAccountId,
            IbkrUsername: paperTrading.IbkrUsername,
            IbkrPassword: paperTrading.IbkrPassword,
            GatewayTimeoutSeconds: paperTrading.GatewayTimeoutSeconds);
    }

    private static bool HasRealCredentialValue(string? value, string fakePlaceholder)
    {
        return !string.IsNullOrWhiteSpace(value) &&
            !string.Equals(value.Trim(), fakePlaceholder, StringComparison.OrdinalIgnoreCase);
    }
}
