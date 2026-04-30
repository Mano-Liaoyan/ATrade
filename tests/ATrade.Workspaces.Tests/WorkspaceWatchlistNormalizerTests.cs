using ATrade.Workspaces;

namespace ATrade.Workspaces.Tests;

public sealed class WorkspaceWatchlistNormalizerTests
{
    [Fact]
    public void NormalizeReplacement_DeduplicatesOnlyExactInstrumentKeysWhilePreservingFirstSeenOrder()
    {
        var normalized = WorkspaceWatchlistNormalizer.NormalizeReplacement(
            new[]
            {
                new WorkspaceWatchlistSymbolInput(" aapl ", Provider: "manual", Name: "Apple manual"),
                new WorkspaceWatchlistSymbolInput("MSFT"),
                new WorkspaceWatchlistSymbolInput(
                    "AAPL",
                    Provider: "IBKR",
                    ProviderSymbolId: "265598",
                    IbkrConid: 265598,
                    Name: "Apple Inc.",
                    Exchange: "nasdaq",
                    Currency: "usd",
                    AssetClass: "stk"),
                new WorkspaceWatchlistSymbolInput(
                    "aapl",
                    Provider: "ibkr",
                    ProviderSymbolId: " 265598 ",
                    IbkrConid: 265598,
                    Name: "Apple Inc. Class A",
                    Exchange: "NASDAQ",
                    Currency: "USD",
                    AssetClass: "STK"),
                new WorkspaceWatchlistSymbolInput("brk.b"),
            });

        Assert.Collection(
            normalized,
            symbol =>
            {
                Assert.Equal("AAPL", symbol.Symbol);
                Assert.Equal(0, symbol.SortOrder);
                Assert.Equal("manual", symbol.Provider);
                Assert.Null(symbol.ProviderSymbolId);
                Assert.Null(symbol.IbkrConid);
                Assert.Equal("Apple manual", symbol.Name);
            },
            symbol =>
            {
                Assert.Equal("MSFT", symbol.Symbol);
                Assert.Equal(1, symbol.SortOrder);
            },
            symbol =>
            {
                Assert.Equal("AAPL", symbol.Symbol);
                Assert.Equal(2, symbol.SortOrder);
                Assert.Equal("ibkr", symbol.Provider);
                Assert.Equal("265598", symbol.ProviderSymbolId);
                Assert.Equal(265598, symbol.IbkrConid);
                Assert.Equal("Apple Inc. Class A", symbol.Name);
                Assert.Equal("NASDAQ", symbol.Exchange);
                Assert.Equal("USD", symbol.Currency);
                Assert.Equal("STK", symbol.AssetClass);
            },
            symbol =>
            {
                Assert.Equal("BRK.B", symbol.Symbol);
                Assert.Equal(3, symbol.SortOrder);
            });
    }

    [Fact]
    public void NormalizeReplacement_KeepsSameSymbolDifferentMarketsAsSeparatePins()
    {
        var normalized = WorkspaceWatchlistNormalizer.NormalizeReplacement(
            new[]
            {
                new WorkspaceWatchlistSymbolInput("BHP", Provider: "ibkr", ProviderSymbolId: "1001", IbkrConid: 1001, Name: "BHP Group", Exchange: "NYSE", Currency: "USD"),
                new WorkspaceWatchlistSymbolInput("BHP", Provider: "ibkr", ProviderSymbolId: "2002", IbkrConid: 2002, Name: "BHP Group", Exchange: "LSE", Currency: "GBP"),
                new WorkspaceWatchlistSymbolInput("BHP", Provider: "ibkr", ProviderSymbolId: "3003", IbkrConid: 3003, Name: "BHP Group", Exchange: "ASX", Currency: "AUD"),
            });

        Assert.Equal(3, normalized.Count);
        Assert.Equal(new[] { "NYSE", "LSE", "ASX" }, normalized.Select(symbol => symbol.Exchange));
        Assert.Equal(3, normalized.Select(symbol => symbol.InstrumentKey).Distinct(StringComparer.OrdinalIgnoreCase).Count());
    }

    [Fact]
    public void Normalize_FillsManualStockDefaultsAndNormalizesMetadataForFutureProviderEnrichment()
    {
        var normalized = WorkspaceWatchlistNormalizer.Normalize(
            new WorkspaceWatchlistSymbolInput(
                Symbol: " msft ",
                Provider: " IBKR ",
                ProviderSymbolId: " 272093 ",
                IbkrConid: 272093,
                Name: " Microsoft Corporation ",
                Exchange: " nasdaq ",
                Currency: " usd ",
                AssetClass: " stk "),
            sortOrder: 7);

        Assert.Equal("MSFT", normalized.Symbol);
        Assert.Equal("ibkr", normalized.Provider);
        Assert.Equal("272093", normalized.ProviderSymbolId);
        Assert.Equal(272093, normalized.IbkrConid);
        Assert.Equal("Microsoft Corporation", normalized.Name);
        Assert.Equal("NASDAQ", normalized.Exchange);
        Assert.Equal("USD", normalized.Currency);
        Assert.Equal("STK", normalized.AssetClass);
        Assert.Equal(7, normalized.SortOrder);
        Assert.Equal("provider=ibkr|providerSymbolId=272093|ibkrConid=272093|symbol=MSFT|exchange=NASDAQ|currency=USD|assetClass=STK", normalized.InstrumentKey);
    }

    [Fact]
    public void Normalize_InfersIbkrProviderSymbolIdFromConidWhenOnlySearchConidIsProvided()
    {
        var normalized = WorkspaceWatchlistNormalizer.Normalize(
            new WorkspaceWatchlistSymbolInput(
                Symbol: " meta ",
                IbkrConid: 107113386,
                Name: "Meta Platforms Inc.",
                Exchange: "nasdaq"));

        Assert.Equal("META", normalized.Symbol);
        Assert.Equal("ibkr", normalized.Provider);
        Assert.Equal("107113386", normalized.ProviderSymbolId);
        Assert.Equal(107113386, normalized.IbkrConid);
        Assert.Equal("Meta Platforms Inc.", normalized.Name);
        Assert.Equal("NASDAQ", normalized.Exchange);
        Assert.Equal("USD", normalized.Currency);
        Assert.Equal("STK", normalized.AssetClass);
    }

    [Fact]
    public void Normalize_UsesManualUsdStockDefaultsWhenMetadataIsMissing()
    {
        var normalized = WorkspaceWatchlistNormalizer.Normalize(new WorkspaceWatchlistSymbolInput("NVDA"));

        Assert.Equal("manual", normalized.Provider);
        Assert.Null(normalized.ProviderSymbolId);
        Assert.Null(normalized.IbkrConid);
        Assert.Null(normalized.Name);
        Assert.Null(normalized.Exchange);
        Assert.Equal("USD", normalized.Currency);
        Assert.Equal("STK", normalized.AssetClass);
        Assert.Equal("provider=manual|providerSymbolId=|ibkrConid=|symbol=NVDA|exchange=|currency=USD|assetClass=STK", normalized.InstrumentKey);
    }
}
