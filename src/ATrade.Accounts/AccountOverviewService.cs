namespace ATrade.Accounts;

public interface IAccountOverviewProvider
{
    AccountOverview GetOverview();
}

public sealed class AccountOverviewService : IAccountOverviewProvider
{
    public AccountOverview GetOverview() => AccountOverview.Bootstrap;
}
