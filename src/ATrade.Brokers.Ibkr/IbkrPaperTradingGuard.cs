using Microsoft.Extensions.Options;

namespace ATrade.Brokers.Ibkr;

public sealed class IbkrPaperTradingGuard(IOptions<IbkrGatewayOptions> gatewayOptions) : IIbkrPaperTradingGuard
{
    public IbkrPaperTradingGuardResult Evaluate()
    {
        var options = gatewayOptions.Value;

        return options.AccountMode == IbkrAccountMode.Paper
            ? IbkrPaperTradingGuardResult.Allowed()
            : IbkrPaperTradingGuardResult.Rejected(options.AccountMode);
    }

    public void EnsurePaperOnly()
    {
        var result = Evaluate();

        if (!result.IsAllowed)
        {
            throw new IbkrPaperTradingRequiredException(result.Message);
        }
    }
}
