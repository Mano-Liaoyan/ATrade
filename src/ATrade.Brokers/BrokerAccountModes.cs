namespace ATrade.Brokers;

public static class BrokerAccountModes
{
    public const string Paper = "paper";
    public const string Live = "live";
    public const string Unknown = "unknown";

    public static string Normalize(string? mode)
    {
        if (string.IsNullOrWhiteSpace(mode))
        {
            return Unknown;
        }

        return mode.Trim().ToLowerInvariant() switch
        {
            Paper => Paper,
            Live => Live,
            _ => Unknown,
        };
    }
}
