using ATrade.Workspaces;

namespace ATrade.Workspaces.Tests;

public sealed class WorkspaceWatchlistNormalizerTests
{
    [Fact]
    public void NormalizeReplacement_DeduplicatesAndEnrichesCaseInsensitiveSymbolsWhilePreservingFirstSeenOrder()
    {
        var normalized = WorkspaceWatchlistNormalizer.NormalizeReplacement(
            new[]
            {
                new WorkspaceWatchlistSymbolInput(" aapl ", Provider: "manual", Name: "Apple Inc."),
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
                new WorkspaceWatchlistSymbolInput("brk.b"),
            });

        Assert.Collection(
            normalized,
            symbol =>
            {
                Assert.Equal("AAPL", symbol.Symbol);
                Assert.Equal(0, symbol.SortOrder);
                Assert.Equal("ibkr", symbol.Provider);
                Assert.Equal("265598", symbol.ProviderSymbolId);
                Assert.Equal(265598, symbol.IbkrConid);
                Assert.Equal("Apple Inc.", symbol.Name);
                Assert.Equal("NASDAQ", symbol.Exchange);
                Assert.Equal("USD", symbol.Currency);
                Assert.Equal("STK", symbol.AssetClass);
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
    public void NormalizeReplacement_DeduplicatesProviderConidsBeforeFallingBackToSymbols()
    {
        var normalized = WorkspaceWatchlistNormalizer.NormalizeReplacement(
            new[]
            {
                new WorkspaceWatchlistSymbolInput("ABC", Provider: "ibkr", ProviderSymbolId: "123", IbkrConid: 123, Name: "ABC Common", Exchange: "nyse"),
                new WorkspaceWatchlistSymbolInput("ABC.W", Provider: "ibkr", ProviderSymbolId: "123", IbkrConid: 123, Name: "ABC Alias", Exchange: "nyse"),
                new WorkspaceWatchlistSymbolInput("abc", Provider: "manual", Name: "ABC Manual"),
                new WorkspaceWatchlistSymbolInput("XYZ"),
                new WorkspaceWatchlistSymbolInput("xyz"),
            });

        Assert.Collection(
            normalized,
            symbol =>
            {
                Assert.Equal("ABC", symbol.Symbol);
                Assert.Equal("ibkr", symbol.Provider);
                Assert.Equal("123", symbol.ProviderSymbolId);
                Assert.Equal(123, symbol.IbkrConid);
                Assert.Equal(0, symbol.SortOrder);
            },
            symbol =>
            {
                Assert.Equal("XYZ", symbol.Symbol);
                Assert.Equal("manual", symbol.Provider);
                Assert.Equal(1, symbol.SortOrder);
            });
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
    }
}
