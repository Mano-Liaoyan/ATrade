namespace ATrade.Accounts;

public sealed record AccountOverview(
    string Module,
    string Status,
    string BrokerConnection,
    IReadOnlyList<AccountOverviewAccount> Accounts)
{
    public static AccountOverview Bootstrap { get; } = new(
        Module: "accounts",
        Status: "bootstrap",
        BrokerConnection: "not-configured",
        Accounts: Array.Empty<AccountOverviewAccount>());
}

public sealed record AccountOverviewAccount;
