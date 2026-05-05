using ATrade.Accounts;

namespace ATrade.Accounts.Tests;

public sealed class LocalPaperCapitalValidatorTests
{
    [Theory]
    [InlineData(1)]
    [InlineData(100000.129)]
    public void Validate_AcceptsPositiveUsdAmountsAndNormalizes(decimal amount)
    {
        var value = LocalPaperCapitalValidator.Validate(new LocalPaperCapitalUpdateRequest(amount, " usd "));

        Assert.True(value.Amount > 0);
        Assert.Equal("USD", value.Currency);
        Assert.Equal(decimal.Round(amount, 2, MidpointRounding.AwayFromZero), value.Amount);
    }

    [Fact]
    public void Validate_DefaultsCurrencyToUsd()
    {
        var value = LocalPaperCapitalValidator.Validate(new LocalPaperCapitalUpdateRequest(50000m, null));

        Assert.Equal(50000m, value.Amount);
        Assert.Equal("USD", value.Currency);
    }

    [Fact]
    public void Validate_RejectsMissingAmount()
    {
        var exception = Assert.Throws<PaperCapitalValidationException>(
            () => LocalPaperCapitalValidator.Validate(new LocalPaperCapitalUpdateRequest(null, "USD")));

        Assert.Equal(PaperCapitalErrorCodes.InvalidAmount, exception.Code);
    }

    [Theory]
    [InlineData("0")]
    [InlineData("-1")]
    public void Validate_RejectsNonPositiveAmounts(string amount)
    {
        var exception = Assert.Throws<PaperCapitalValidationException>(
            () => LocalPaperCapitalValidator.Validate(new LocalPaperCapitalUpdateRequest(decimal.Parse(amount), "USD")));

        Assert.Equal(PaperCapitalErrorCodes.InvalidAmount, exception.Code);
    }

    [Theory]
    [InlineData("EUR")]
    [InlineData("USDT")]
    public void Validate_RejectsUnsupportedCurrencies(string currency)
    {
        var exception = Assert.Throws<PaperCapitalValidationException>(
            () => LocalPaperCapitalValidator.Validate(new LocalPaperCapitalUpdateRequest(1000m, currency)));

        Assert.Equal(PaperCapitalErrorCodes.InvalidCurrency, exception.Code);
        Assert.DoesNotContain("account", exception.Message, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("token", exception.Message, StringComparison.OrdinalIgnoreCase);
    }
}
