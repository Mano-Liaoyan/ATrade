using ATrade.Brokers;

namespace ATrade.Brokers.Ibkr;

public static class IbkrBrokerAdapterCapabilities
{
    public static BrokerProviderCapabilities PaperSafeReadOnly { get; } = BrokerProviderCapabilities.PaperSafeStatusOnly;
}
