namespace ATrade.Brokers.Ibkr;

public sealed record IbkrAccountSummaryBalance(decimal Amount, string Currency, string Metric);
