namespace ATrade.Brokers.Ibkr;

public sealed class IbkrPaperTradingRequiredException(string message) : InvalidOperationException(message);
