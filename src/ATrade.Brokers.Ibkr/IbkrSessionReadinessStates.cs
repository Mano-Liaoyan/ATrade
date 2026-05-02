namespace ATrade.Brokers.Ibkr;

public static class IbkrSessionReadinessStates
{
    public const string Disabled = "disabled";
    public const string RejectedLiveMode = "rejected-live-mode";
    public const string NotConfigured = "not-configured";
    public const string CredentialsMissing = "credentials-missing";
    public const string IbeamContainerConfigured = "ibeam-container-configured";
    public const string Error = "error";
    public const string Authenticated = "authenticated";
    public const string Connecting = "connecting";
    public const string Degraded = "degraded";
}
