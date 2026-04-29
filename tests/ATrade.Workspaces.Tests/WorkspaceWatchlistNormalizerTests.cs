using ATrade.Workspaces;

namespace ATrade.Workspaces.Tests;

public sealed class WorkspaceWatchlistNormalizerTests
{
    [Fact]
    public void NormalizeReplacement_DeduplicatesCaseInsensitiveSymbolsAndPreservesFirstSeenOrder()
    {
        var normalized = WorkspaceWatchlistNormalizer.NormalizeReplacement(
            new[]
            {
                new WorkspaceWatchlistSymbolInput(" aapl ", Provider: "manual", Name: "Apple Inc."),
                new WorkspaceWatchlistSymbolInput("MSFT"),
                new WorkspaceWatchlistSymbolInput("AAPL", Provider: "ibkr", IbkrConid: 265598),
                new WorkspaceWatchlistSymbolInput("brk.b"),
            });

        Assert.Collection(
            normalized,
            symbol =>
            {
                Assert.Equal("AAPL", symbol.Symbol);
                Assert.Equal(0, symbol.SortOrder);
                Assert.Equal("manual", symbol.Provider);
                Assert.Equal("Apple Inc.", symbol.Name);
            },
            symbol =>
            {
                Assert.Equal("MSFT", symbol.Symbol);
                Assert.Equal(1, symbol.SortOrder);
            },
            symbol =>
            {
                Assert.Equal("BRK.B", symbol.Symbol);
                Assert.Equal(2, symbol.SortOrder);
            });
    }

    [Fact]
    public void Normalize_FillsManualStockDefaultsAndNormalizesMetadataForFutureProviderEnrichment()
    {
        var normalized = WorkspaceWatchlistNormalizer.Normalize(
            new WorkspaceWatchlistSymbolInput(
                Symbol: " msft ",
                Provider: " ibkr ",
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
    }
}
