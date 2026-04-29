using ATrade.Workspaces;

namespace ATrade.Workspaces.Tests;

public sealed class WorkspaceSymbolNormalizerTests
{
    [Theory]
    [InlineData(" aapl ", "AAPL")]
    [InlineData("brk.b", "BRK.B")]
    [InlineData("rds-a", "RDS-A")]
    [InlineData("spy_etf", "SPY_ETF")]
    [InlineData("1234", "1234")]
    public void Normalize_TrimsAndUppercasesAllowedProviderNeutralSymbols(string input, string expected)
    {
        var normalized = WorkspaceSymbolNormalizer.Normalize(input);

        Assert.Equal(expected, normalized);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("$SPY")]
    [InlineData("SPY/NYSE")]
    [InlineData("ABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFG")]
    public void TryNormalize_RejectsInvalidSymbols(string? input)
    {
        var isValid = WorkspaceSymbolNormalizer.TryNormalize(input, out var normalized, out var error);

        Assert.False(isValid);
        Assert.Equal(string.Empty, normalized);
        Assert.NotEmpty(error);
    }
}
