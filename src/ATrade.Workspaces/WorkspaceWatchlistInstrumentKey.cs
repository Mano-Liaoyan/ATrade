using ATrade.MarketData;

namespace ATrade.Workspaces;

internal static class WorkspaceWatchlistInstrumentKey
{
    public static string Create(
        string symbol,
        string provider,
        string? providerSymbolId,
        long? ibkrConid,
        string? exchange,
        string? currency,
        string? assetClass) => ExactInstrumentIdentity
            .Create(symbol, provider, providerSymbolId, ibkrConid, exchange, currency, assetClass)
            .InstrumentKey;

    public static string NormalizeExistingKey(string? instrumentKey)
    {
        if (ExactInstrumentIdentity.TryNormalizeExistingInstrumentKey(instrumentKey, out var normalized, out var error))
        {
            return normalized;
        }

        throw new WorkspaceWatchlistValidationException(
            WorkspaceWatchlistErrorCodes.InvalidInstrumentKey,
            error);
    }
}
