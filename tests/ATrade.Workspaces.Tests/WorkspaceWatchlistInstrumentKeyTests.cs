using System.Text.Json;
using ATrade.Workspaces;

namespace ATrade.Workspaces.Tests;

public sealed class WorkspaceWatchlistInstrumentKeyTests
{
    [Fact]
    public void Normalize_CreatesStableProviderMarketInstrumentKey()
    {
        var normalized = WorkspaceWatchlistNormalizer.Normalize(
            new WorkspaceWatchlistSymbolInput(
                Symbol: " aapl ",
                Provider: " IBKR ",
                ProviderSymbolId: " 265598 ",
                IbkrConid: 265598,
                Name: "Apple Inc.",
                Exchange: " nasdaq ",
                Currency: " usd ",
                AssetClass: " stk "));

        Assert.Equal(
            "provider=ibkr|providerSymbolId=265598|ibkrConid=265598|symbol=AAPL|exchange=NASDAQ|currency=USD|assetClass=STK",
            normalized.InstrumentKey);
    }

    [Fact]
    public void Normalize_DistinguishesSameSymbolAcrossProviderMarketIdentity()
    {
        var nasdaq = WorkspaceWatchlistNormalizer.Normalize(
            new WorkspaceWatchlistSymbolInput("AAPL", Provider: "ibkr", ProviderSymbolId: "265598", IbkrConid: 265598, Exchange: "NASDAQ", Currency: "USD", AssetClass: "STK"));
        var lse = WorkspaceWatchlistNormalizer.Normalize(
            new WorkspaceWatchlistSymbolInput("AAPL", Provider: "ibkr", ProviderSymbolId: "493546048", IbkrConid: 493546048, Exchange: "LSE", Currency: "GBP", AssetClass: "STK"));
        var manual = WorkspaceWatchlistNormalizer.Normalize(new WorkspaceWatchlistSymbolInput("AAPL"));

        Assert.NotEqual(nasdaq.InstrumentKey, lse.InstrumentKey);
        Assert.NotEqual(nasdaq.InstrumentKey, manual.InstrumentKey);
        Assert.NotEqual(lse.InstrumentKey, manual.InstrumentKey);
    }

    [Fact]
    public void WatchlistSymbolJson_ExposesInstrumentKeyAndPinKeyAliases()
    {
        const string key = "provider=ibkr|providerSymbolId=265598|ibkrConid=265598|symbol=AAPL|exchange=NASDAQ|currency=USD|assetClass=STK";
        var symbol = new WorkspaceWatchlistSymbol(
            "AAPL",
            key,
            key,
            "ibkr",
            "265598",
            265598,
            "Apple Inc.",
            "NASDAQ",
            "USD",
            "STK",
            0,
            DateTimeOffset.UnixEpoch,
            DateTimeOffset.UnixEpoch);

        var json = JsonSerializer.Serialize(symbol, new JsonSerializerOptions(JsonSerializerDefaults.Web));

        Assert.Contains("\"instrumentKey\":\"" + key + "\"", json, StringComparison.Ordinal);
        Assert.Contains("\"pinKey\":\"" + key + "\"", json, StringComparison.Ordinal);
    }

    [Fact]
    public void NormalizeExistingKey_RejectsBlankExactDeleteKeys()
    {
        var exception = Assert.Throws<WorkspaceWatchlistValidationException>(() => WorkspaceWatchlistInstrumentKey.NormalizeExistingKey("   "));

        Assert.Equal(WorkspaceWatchlistErrorCodes.InvalidInstrumentKey, exception.Code);
    }
}
