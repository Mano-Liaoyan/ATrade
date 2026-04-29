namespace ATrade.Brokers.Ibkr;

public sealed record IbkrGatewaySessionStatus(
    bool Authenticated,
    bool Connected,
    bool Competing,
    string? Message,
    string? ServerName,
    string? ServerVersion);
