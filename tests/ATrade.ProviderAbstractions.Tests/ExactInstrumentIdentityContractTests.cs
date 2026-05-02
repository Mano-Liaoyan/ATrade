using ATrade.MarketData;

namespace ATrade.ProviderAbstractions.Tests;

public sealed class ExactInstrumentIdentityContractTests
{
    [Fact]
    public void Create_NormalizesProviderMarketIdentityAndStableInstrumentKey()
    {
        var identity = ExactInstrumentIdentity.Create(
            symbol: " aapl ",
            provider: " IBKR ",
            providerSymbolId: " 265598 ",
            ibkrConid: 265598,
            exchange: " nasdaq ",
            currency: " usd ",
            assetClass: " stock ");

        Assert.Equal("ibkr", identity.Provider);
        Assert.Equal("265598", identity.ProviderSymbolId);
        Assert.Equal(265598, identity.IbkrConid);
        Assert.Equal("AAPL", identity.Symbol);
        Assert.Equal("NASDAQ", identity.Exchange);
        Assert.Equal("USD", identity.Currency);
        Assert.Equal(MarketDataAssetClasses.Stock, identity.AssetClass);
        Assert.Equal(
            "provider=ibkr|providerSymbolId=265598|ibkrConid=265598|symbol=AAPL|exchange=NASDAQ|currency=USD|assetClass=STK",
            identity.InstrumentKey);
    }

    [Fact]
    public void Create_DistinguishesSameSymbolAcrossProviderMarketIdentity()
    {
        var nasdaq = ExactInstrumentIdentity.Create("AAPL", "ibkr", "265598", 265598, "NASDAQ", "USD", "STK");
        var lse = ExactInstrumentIdentity.Create("aapl", "ibkr", "493546048", 493546048, "lse", "gbp", "stock");
        var manual = ExactInstrumentIdentity.Create("AAPL");

        Assert.NotEqual(nasdaq, lse);
        Assert.NotEqual(nasdaq, manual);
        Assert.NotEqual(lse, manual);
        Assert.Equal(3, new[] { nasdaq.InstrumentKey, lse.InstrumentKey, manual.InstrumentKey }.Distinct(StringComparer.OrdinalIgnoreCase).Count());
    }

    [Fact]
    public void Create_PreservesManualLegacyIdentityDefaults()
    {
        var manual = ExactInstrumentIdentity.Create(" nvda ");

        Assert.Equal(ExactInstrumentIdentityProviders.Manual, manual.Provider);
        Assert.Null(manual.ProviderSymbolId);
        Assert.Null(manual.IbkrConid);
        Assert.Equal("NVDA", manual.Symbol);
        Assert.Null(manual.Exchange);
        Assert.Equal(ExactInstrumentIdentityDefaults.DefaultCurrency, manual.Currency);
        Assert.Equal(ExactInstrumentIdentityDefaults.DefaultAssetClass, manual.AssetClass);
        Assert.Equal(
            "provider=manual|providerSymbolId=|ibkrConid=|symbol=NVDA|exchange=|currency=USD|assetClass=STK",
            manual.InstrumentKey);
    }

    [Fact]
    public void MarketDataSymbolIdentity_ProjectsThroughExactInstrumentIdentity()
    {
        var projected = MarketDataSymbolIdentity.Create(
            symbol: " msft ",
            provider: " IBKR ",
            providerSymbolId: " 272093 ",
            assetClass: " Stock ",
            exchange: " nasdaq ",
            currency: " usd ",
            ibkrConid: 272093);
        var exact = projected.ToExactInstrumentIdentity(272093);

        Assert.Equal("MSFT", projected.Symbol);
        Assert.Equal("ibkr", projected.Provider);
        Assert.Equal("272093", projected.ProviderSymbolId);
        Assert.Equal(MarketDataAssetClasses.Stock, projected.AssetClass);
        Assert.Equal("NASDAQ", projected.Exchange);
        Assert.Equal("USD", projected.Currency);
        Assert.Equal(exact.ToMarketDataSymbolIdentity(), projected);
        Assert.Equal(
            "provider=ibkr|providerSymbolId=272093|ibkrConid=272093|symbol=MSFT|exchange=NASDAQ|currency=USD|assetClass=STK",
            exact.InstrumentKey);
    }
}
