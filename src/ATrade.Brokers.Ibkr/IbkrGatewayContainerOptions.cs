namespace ATrade.Brokers.Ibkr;

public sealed class IbkrGatewayContainerOptions
{
    public string? Image { get; set; }

    public int? Port { get; set; } = 5000;
}
