using Microsoft.Extensions.Configuration;

namespace ATrade.Brokers.Ibkr;

public sealed class IbkrGatewayOptions
{
    public const int DefaultTimeoutSeconds = 15;

    public bool IntegrationEnabled { get; set; }

    public IbkrAccountMode AccountMode { get; set; } = IbkrAccountMode.Paper;

    public Uri? GatewayBaseUrl { get; set; } = new("http://127.0.0.1:5000", UriKind.Absolute);

    public string? PaperAccountId { get; set; }

    public TimeSpan RequestTimeout { get; set; } = TimeSpan.FromSeconds(DefaultTimeoutSeconds);

    public IbkrGatewayContainerOptions GatewayContainer { get; set; } = new();

    public static IbkrGatewayOptions FromConfiguration(IConfiguration configuration)
    {
        ArgumentNullException.ThrowIfNull(configuration);

        var options = new IbkrGatewayOptions();
        var configuredIntegrationEnabled = configuration.GetValue<bool?>(IbkrGatewayEnvironmentVariables.IntegrationEnabled);
        var configuredTimeoutSeconds = configuration.GetValue<double?>(IbkrGatewayEnvironmentVariables.GatewayTimeoutSeconds);
        var configuredGatewayPort = configuration.GetValue<int?>(IbkrGatewayEnvironmentVariables.GatewayPort);
        var configuredGatewayUrl = NullIfWhiteSpace(configuration[IbkrGatewayEnvironmentVariables.GatewayUrl]);
        var configuredGatewayImage = NullIfWhiteSpace(configuration[IbkrGatewayEnvironmentVariables.GatewayImage]);
        var configuredPaperAccountId = NullIfWhiteSpace(configuration[IbkrGatewayEnvironmentVariables.PaperAccountId]);
        var configuredAccountMode = NullIfWhiteSpace(configuration[IbkrGatewayEnvironmentVariables.AccountMode]);

        if (configuredIntegrationEnabled.HasValue)
        {
            options.IntegrationEnabled = configuredIntegrationEnabled.Value;
        }

        if (TryParseAccountMode(configuredAccountMode, out var accountMode))
        {
            options.AccountMode = accountMode;
        }

        if (configuredGatewayUrl is not null
            && Uri.TryCreate(configuredGatewayUrl, UriKind.Absolute, out var gatewayBaseUrl))
        {
            options.GatewayBaseUrl = gatewayBaseUrl;
        }

        if (configuredTimeoutSeconds is > 0)
        {
            options.RequestTimeout = TimeSpan.FromSeconds(configuredTimeoutSeconds.Value);
        }

        options.PaperAccountId = configuredPaperAccountId;
        options.GatewayContainer.Image = configuredGatewayImage;

        if (configuredGatewayPort is > 0)
        {
            options.GatewayContainer.Port = configuredGatewayPort.Value;
        }

        return options;
    }

    public static bool TryParseAccountMode(string? value, out IbkrAccountMode mode)
    {
        if (Enum.TryParse(value, ignoreCase: true, out mode))
        {
            return true;
        }

        mode = default;
        return false;
    }

    private static string? NullIfWhiteSpace(string? value)
    {
        return string.IsNullOrWhiteSpace(value)
            ? null
            : value.Trim();
    }
}
