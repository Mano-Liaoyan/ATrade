namespace ATrade.Brokers.Ibkr;

public static class IbkrGatewayEnvironmentVariables
{
    public const string IntegrationEnabled = "ATRADE_BROKER_INTEGRATION_ENABLED";
    public const string AccountMode = "ATRADE_BROKER_ACCOUNT_MODE";
    public const string GatewayUrl = "ATRADE_IBKR_GATEWAY_URL";
    public const string GatewayPort = "ATRADE_IBKR_GATEWAY_PORT";
    public const string GatewayImage = "ATRADE_IBKR_GATEWAY_IMAGE";
    public const string PaperAccountId = "ATRADE_IBKR_PAPER_ACCOUNT_ID";
    public const string Username = "ATRADE_IBKR_USERNAME";
    public const string Password = "ATRADE_IBKR_PASSWORD";
    public const string GatewayTimeoutSeconds = "ATRADE_IBKR_GATEWAY_TIMEOUT_SECONDS";

    public const string IbeamAccount = "IBEAM_ACCOUNT";
    public const string IbeamPassword = "IBEAM_PASSWORD";
}

public static class IbkrGatewayPlaceholderValues
{
    public const string Username = "IBKR_USERNAME";
    public const string Password = "IBKR_PASSWORD";
    public const string PaperAccountId = "IBKR_ACCOUNT_ID";
}
