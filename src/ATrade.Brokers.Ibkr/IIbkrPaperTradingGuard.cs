namespace ATrade.Brokers.Ibkr;

public interface IIbkrPaperTradingGuard
{
    IbkrPaperTradingGuardResult Evaluate();

    void EnsurePaperOnly();
}
