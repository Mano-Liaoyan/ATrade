using System.Text.Json;
using ATrade.Backtesting;
using ATrade.MarketData;

namespace ATrade.Backtesting.Tests;

public sealed class BacktestRequestValidatorTests
{
    [Fact]
    public void Validate_NormalizesSingleSymbolBuiltInStrategyParameterBagAndCosts()
    {
        var request = new BacktestCreateRequest(
            Symbol: MarketDataSymbolIdentity.Create("aapl", "ibkr", "265598", MarketDataAssetClasses.Stock, "nasdaq", "usd"),
            SymbolCode: "AAPL",
            StrategyId: "SMA-CROSSOVER",
            Parameters: new Dictionary<string, JsonElement>
            {
                ["fastPeriod"] = Json("20"),
                ["slowPeriod"] = Json("50"),
                ["risk"] = Json("{\"maxPositionPercent\":25}")
            },
            ChartRange: "1y",
            CostModel: new BacktestCostModel(1.23456m, 2.34567m, "usd"),
            SlippageBps: 4.56789m,
            BenchmarkMode: "BUY-AND-HOLD");

        var snapshot = BacktestRequestValidator.Validate(request);

        Assert.Equal("AAPL", snapshot.Symbol.Symbol);
        Assert.Equal(BacktestStrategyIds.SmaCrossover, snapshot.StrategyId);
        Assert.Equal(ChartRangePresets.OneYear, snapshot.ChartRange);
        Assert.Equal(3, snapshot.Parameters.Count);
        Assert.Equal(1.2346m, snapshot.CostModel.CommissionPerTrade);
        Assert.Equal(2.3457m, snapshot.CostModel.CommissionBps);
        Assert.Equal("USD", snapshot.CostModel.Currency);
        Assert.Equal(4.5679m, snapshot.SlippageBps);
        Assert.Equal(BacktestBenchmarkModes.BuyAndHold, snapshot.BenchmarkMode);
    }

    [Fact]
    public void Validate_RejectsUnsupportedStrategyIdsInsteadOfCustomStrategies()
    {
        var exception = Assert.Throws<BacktestValidationException>(() =>
            BacktestRequestValidator.Validate(ValidRequest(strategyId: "my-custom-strategy")));

        Assert.Equal(BacktestErrorCodes.UnsupportedStrategy, exception.Code);
        Assert.Contains(BacktestStrategyIds.SupportedValuesMessage, exception.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void Validate_RejectsUnsupportedChartRanges()
    {
        var exception = Assert.Throws<BacktestValidationException>(() =>
            BacktestRequestValidator.Validate(ValidRequest(chartRange: "2y")));

        Assert.Equal(BacktestErrorCodes.UnsupportedChartRange, exception.Code);
    }

    [Fact]
    public void Validate_RejectsDirectBrowserBars()
    {
        var request = ValidRequest() with
        {
            AdditionalProperties = new Dictionary<string, JsonElement>
            {
                ["bars"] = Json("[]"),
            },
        };

        var exception = Assert.Throws<BacktestValidationException>(() => BacktestRequestValidator.Validate(request));

        Assert.Equal(BacktestErrorCodes.ForbiddenField, exception.Code);
        Assert.Equal(BacktestSafeMessages.DirectBarsNotAllowed, exception.Message);
    }

    [Fact]
    public void Validate_RejectsCustomCodeFieldsInPayloadAndParameterBag()
    {
        var payload = ValidRequest() with
        {
            AdditionalProperties = new Dictionary<string, JsonElement>
            {
                ["script"] = Json("\"print(1)\""),
            },
        };
        var parameters = ValidRequest(parameters: new Dictionary<string, JsonElement>
        {
            ["strategyCode"] = Json("\"return buy\""),
        });

        var payloadException = Assert.Throws<BacktestValidationException>(() => BacktestRequestValidator.Validate(payload));
        var parameterException = Assert.Throws<BacktestValidationException>(() => BacktestRequestValidator.Validate(parameters));

        Assert.Equal(BacktestErrorCodes.ForbiddenField, payloadException.Code);
        Assert.Equal(BacktestSafeMessages.CustomCodeNotAllowed, payloadException.Message);
        Assert.Equal(BacktestErrorCodes.ForbiddenField, parameterException.Code);
        Assert.Equal(BacktestSafeMessages.CustomCodeNotAllowed, parameterException.Message);
    }

    [Fact]
    public void Validate_RejectsOrderRoutingAndAccountFields()
    {
        var request = ValidRequest() with
        {
            AdditionalProperties = new Dictionary<string, JsonElement>
            {
                ["orderType"] = Json("\"MKT\""),
            },
        };
        var accountPayload = ValidRequest() with
        {
            AdditionalProperties = new Dictionary<string, JsonElement>
            {
                ["accountId"] = Json("\"DU1234567\""),
            },
        };

        var orderException = Assert.Throws<BacktestValidationException>(() => BacktestRequestValidator.Validate(request));
        var accountException = Assert.Throws<BacktestValidationException>(() => BacktestRequestValidator.Validate(accountPayload));

        Assert.Equal(BacktestErrorCodes.ForbiddenField, orderException.Code);
        Assert.Equal(BacktestSafeMessages.OrderRoutingNotAllowed, orderException.Message);
        Assert.Equal(BacktestErrorCodes.ForbiddenField, accountException.Code);
        Assert.Equal(BacktestSafeMessages.OrderRoutingNotAllowed, accountException.Message);
    }

    [Fact]
    public void Validate_RejectsMultiSymbolScopes()
    {
        var request = ValidRequest() with
        {
            AdditionalProperties = new Dictionary<string, JsonElement>
            {
                ["symbols"] = Json("[\"AAPL\",\"MSFT\"]"),
            },
        };

        var exception = Assert.Throws<BacktestValidationException>(() => BacktestRequestValidator.Validate(request));

        Assert.Equal(BacktestErrorCodes.UnsupportedScope, exception.Code);
    }

    [Fact]
    public void PublicContracts_DoNotExposeOrderRoutingFields()
    {
        var contractTypes = new[]
        {
            typeof(BacktestCreateRequest),
            typeof(BacktestRequestSnapshot),
            typeof(BacktestRunEnvelope),
            typeof(BacktestRunRecord),
        };

        foreach (var type in contractTypes)
        {
            Assert.DoesNotContain(type.GetProperties(), property => IsOrderRoutingProperty(property.Name));
        }
    }

    private static BacktestCreateRequest ValidRequest(
        string strategyId = BacktestStrategyIds.SmaCrossover,
        string chartRange = ChartRangePresets.OneYear,
        IDictionary<string, JsonElement>? parameters = null) => new(
            Symbol: MarketDataSymbolIdentity.Create("AAPL", "ibkr", "265598", MarketDataAssetClasses.Stock, "NASDAQ", "USD"),
            SymbolCode: null,
            StrategyId: strategyId,
            Parameters: parameters ?? new Dictionary<string, JsonElement>
            {
                ["fastPeriod"] = Json("20"),
                ["slowPeriod"] = Json("50"),
            },
            ChartRange: chartRange,
            CostModel: new BacktestCostModel(0m, 0m, "USD"),
            SlippageBps: 0m,
            BenchmarkMode: BacktestBenchmarkModes.None);

    private static JsonElement Json(string json)
    {
        using var document = JsonDocument.Parse(json);
        return document.RootElement.Clone();
    }

    private static bool IsOrderRoutingProperty(string propertyName) =>
        propertyName.Contains("Order", StringComparison.OrdinalIgnoreCase) ||
        propertyName.Contains("Account", StringComparison.OrdinalIgnoreCase) ||
        propertyName.Contains("Credential", StringComparison.OrdinalIgnoreCase) ||
        propertyName.Contains("Password", StringComparison.OrdinalIgnoreCase) ||
        propertyName.Contains("Token", StringComparison.OrdinalIgnoreCase) ||
        propertyName.Contains("Cookie", StringComparison.OrdinalIgnoreCase) ||
        propertyName.Contains("Session", StringComparison.OrdinalIgnoreCase) ||
        propertyName.Contains("Gateway", StringComparison.OrdinalIgnoreCase);
}
