using System.Text.Json;
using ATrade.Backtesting;
using ATrade.MarketData;

namespace ATrade.Backtesting.Tests;

public sealed class BacktestRequestValidatorTests
{
    [Fact]
    public void BuiltInStrategyDefinitions_ExposeStableIdsLabelsAndDefaultParameters()
    {
        Assert.Equal(
            [BacktestStrategyIds.SmaCrossover, BacktestStrategyIds.RsiMeanReversion, BacktestStrategyIds.Breakout],
            BacktestStrategyCatalog.BuiltIn.Select(strategy => strategy.Id));

        var sma = BacktestStrategyCatalog.GetDefinition(BacktestStrategyIds.SmaCrossover);
        Assert.Equal("SMA crossover", sma.DisplayName);
        Assert.Equal(
            [BacktestStrategyParameterNames.SmaShortWindow, BacktestStrategyParameterNames.SmaLongWindow],
            sma.ParameterNames);
        Assert.Equal(20m, sma.Parameters.Single(parameter => parameter.Name == BacktestStrategyParameterNames.SmaShortWindow).DefaultValue);
        Assert.Equal(50m, sma.Parameters.Single(parameter => parameter.Name == BacktestStrategyParameterNames.SmaLongWindow).DefaultValue);

        var rsi = BacktestStrategyCatalog.GetDefinition(BacktestStrategyIds.RsiMeanReversion);
        Assert.Equal("RSI mean reversion", rsi.DisplayName);
        Assert.Equal(
            [
                BacktestStrategyParameterNames.RsiPeriod,
                BacktestStrategyParameterNames.RsiOversoldThreshold,
                BacktestStrategyParameterNames.RsiOverboughtThreshold,
            ],
            rsi.ParameterNames);
        Assert.Equal(14m, rsi.Parameters.Single(parameter => parameter.Name == BacktestStrategyParameterNames.RsiPeriod).DefaultValue);
        Assert.Equal(30m, rsi.Parameters.Single(parameter => parameter.Name == BacktestStrategyParameterNames.RsiOversoldThreshold).DefaultValue);
        Assert.Equal(70m, rsi.Parameters.Single(parameter => parameter.Name == BacktestStrategyParameterNames.RsiOverboughtThreshold).DefaultValue);

        var breakout = BacktestStrategyCatalog.GetDefinition(BacktestStrategyIds.Breakout);
        Assert.Equal("Breakout", breakout.DisplayName);
        Assert.Equal([BacktestStrategyParameterNames.BreakoutLookbackWindow], breakout.ParameterNames);
        Assert.Equal(20m, breakout.Parameters.Single().DefaultValue);
    }

    [Fact]
    public void Validate_NormalizesSingleSymbolBuiltInStrategyParameterBagAndCosts()
    {
        var request = new BacktestCreateRequest(
            Symbol: MarketDataSymbolIdentity.Create("aapl", "ibkr", "265598", MarketDataAssetClasses.Stock, "nasdaq", "usd"),
            SymbolCode: "AAPL",
            StrategyId: "SMA-CROSSOVER",
            Parameters: new Dictionary<string, JsonElement>
            {
                [BacktestStrategyParameterNames.SmaShortWindow] = Json("12"),
                [BacktestStrategyParameterNames.SmaLongWindow] = Json("40"),
            },
            ChartRange: "1y",
            CostModel: new BacktestCostModel(1.23456m, 2.34567m, "usd"),
            SlippageBps: 4.56789m,
            BenchmarkMode: "BUY-AND-HOLD",
            EngineId: "LEAN");

        var snapshot = BacktestRequestValidator.Validate(request);

        Assert.Equal("AAPL", snapshot.Symbol.Symbol);
        Assert.Equal(BacktestStrategyIds.SmaCrossover, snapshot.StrategyId);
        Assert.Equal(ChartRangePresets.OneYear, snapshot.ChartRange);
        Assert.Equal(2, snapshot.Parameters.Count);
        Assert.Equal(12, snapshot.Parameters[BacktestStrategyParameterNames.SmaShortWindow].GetInt32());
        Assert.Equal(40, snapshot.Parameters[BacktestStrategyParameterNames.SmaLongWindow].GetInt32());
        Assert.Equal(1.2346m, snapshot.CostModel.CommissionPerTrade);
        Assert.Equal(2.3457m, snapshot.CostModel.CommissionBps);
        Assert.Equal("USD", snapshot.CostModel.Currency);
        Assert.Equal(4.5679m, snapshot.SlippageBps);
        Assert.Equal(BacktestBenchmarkModes.BuyAndHold, snapshot.BenchmarkMode);
        Assert.Equal("lean", snapshot.EngineId);
    }

    [Fact]
    public void Validate_DefaultsMissingParametersPerStrategy()
    {
        var sma = BacktestRequestValidator.Validate(ValidRequest(strategyId: BacktestStrategyIds.SmaCrossover, parameters: null));
        Assert.Equal(20, sma.Parameters[BacktestStrategyParameterNames.SmaShortWindow].GetInt32());
        Assert.Equal(50, sma.Parameters[BacktestStrategyParameterNames.SmaLongWindow].GetInt32());

        var rsi = BacktestRequestValidator.Validate(ValidRequest(strategyId: BacktestStrategyIds.RsiMeanReversion, parameters: null));
        Assert.Equal(14, rsi.Parameters[BacktestStrategyParameterNames.RsiPeriod].GetInt32());
        Assert.Equal(30m, rsi.Parameters[BacktestStrategyParameterNames.RsiOversoldThreshold].GetDecimal());
        Assert.Equal(70m, rsi.Parameters[BacktestStrategyParameterNames.RsiOverboughtThreshold].GetDecimal());

        var breakout = BacktestRequestValidator.Validate(ValidRequest(strategyId: BacktestStrategyIds.Breakout, parameters: null));
        Assert.Equal(20, breakout.Parameters[BacktestStrategyParameterNames.BreakoutLookbackWindow].GetInt32());
    }

    [Fact]
    public void Validate_AllowsPartialOverridesAndKeepsStrategyDefaults()
    {
        var rsi = BacktestRequestValidator.Validate(ValidRequest(
            strategyId: BacktestStrategyIds.RsiMeanReversion,
            parameters: new Dictionary<string, JsonElement>
            {
                [BacktestStrategyParameterNames.RsiOversoldThreshold] = Json("25.12345"),
            }));

        Assert.Equal(14, rsi.Parameters[BacktestStrategyParameterNames.RsiPeriod].GetInt32());
        Assert.Equal(25.1235m, rsi.Parameters[BacktestStrategyParameterNames.RsiOversoldThreshold].GetDecimal());
        Assert.Equal(70m, rsi.Parameters[BacktestStrategyParameterNames.RsiOverboughtThreshold].GetDecimal());
    }

    [Theory]
    [InlineData(BacktestStrategyIds.SmaCrossover, BacktestStrategyParameterNames.SmaShortWindow)]
    [InlineData(BacktestStrategyIds.RsiMeanReversion, BacktestStrategyParameterNames.RsiPeriod)]
    [InlineData(BacktestStrategyIds.Breakout, BacktestStrategyParameterNames.BreakoutLookbackWindow)]
    public void PersistedRequestSnapshots_RoundTripBuiltInStrategyDefaults(string strategyId, string expectedParameterName)
    {
        var snapshot = BacktestRequestValidator.Validate(ValidRequest(strategyId: strategyId, parameters: null));

        var serialized = BacktestPersistenceSafety.SerializeRequestSnapshot(snapshot);
        var restored = BacktestPersistenceSafety.DeserializeRequestSnapshot(serialized);

        Assert.Equal(strategyId, restored.StrategyId);
        Assert.True(restored.Parameters.ContainsKey(expectedParameterName));
        Assert.Equal(
            snapshot.Parameters[expectedParameterName].GetRawText(),
            restored.Parameters[expectedParameterName].GetRawText());
        Assert.DoesNotContain("fastPeriod", serialized, StringComparison.Ordinal);
        Assert.DoesNotContain("script", serialized, StringComparison.OrdinalIgnoreCase);
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
    public void Validate_RejectsUnknownAndInvalidStrategyParameters()
    {
        var unknown = Assert.Throws<BacktestValidationException>(() => BacktestRequestValidator.Validate(ValidRequest(
            parameters: new Dictionary<string, JsonElement>
            {
                ["fastPeriod"] = Json("10"),
            })));
        var nonNumeric = Assert.Throws<BacktestValidationException>(() => BacktestRequestValidator.Validate(ValidRequest(
            parameters: new Dictionary<string, JsonElement>
            {
                [BacktestStrategyParameterNames.SmaShortWindow] = Json("\"20\""),
            })));
        var outOfRange = Assert.Throws<BacktestValidationException>(() => BacktestRequestValidator.Validate(ValidRequest(
            strategyId: BacktestStrategyIds.Breakout,
            parameters: new Dictionary<string, JsonElement>
            {
                [BacktestStrategyParameterNames.BreakoutLookbackWindow] = Json("1"),
            })));

        Assert.Equal(BacktestErrorCodes.InvalidParameters, unknown.Code);
        Assert.Contains("fastPeriod", unknown.Message, StringComparison.Ordinal);
        Assert.Equal(BacktestErrorCodes.InvalidParameters, nonNumeric.Code);
        Assert.Equal(BacktestErrorCodes.InvalidParameters, outOfRange.Code);
    }

    [Fact]
    public void Validate_RejectsInvalidStrategyParameterRelationships()
    {
        var sma = Assert.Throws<BacktestValidationException>(() => BacktestRequestValidator.Validate(ValidRequest(
            strategyId: BacktestStrategyIds.SmaCrossover,
            parameters: new Dictionary<string, JsonElement>
            {
                [BacktestStrategyParameterNames.SmaShortWindow] = Json("50"),
                [BacktestStrategyParameterNames.SmaLongWindow] = Json("50"),
            })));
        var rsi = Assert.Throws<BacktestValidationException>(() => BacktestRequestValidator.Validate(ValidRequest(
            strategyId: BacktestStrategyIds.RsiMeanReversion,
            parameters: new Dictionary<string, JsonElement>
            {
                [BacktestStrategyParameterNames.RsiOversoldThreshold] = Json("60"),
                [BacktestStrategyParameterNames.RsiOverboughtThreshold] = Json("59"),
            })));

        Assert.Equal(BacktestErrorCodes.InvalidParameters, sma.Code);
        Assert.Contains("shortWindow", sma.Message, StringComparison.Ordinal);
        Assert.Equal(BacktestErrorCodes.InvalidParameters, rsi.Code);
        Assert.Contains("oversoldThreshold", rsi.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void Validate_RejectsInvalidCostAndSlippageInputs()
    {
        var negativeCommission = Assert.Throws<BacktestValidationException>(() => BacktestRequestValidator.Validate(
            ValidRequest() with { CostModel = new BacktestCostModel(-0.01m, 0m, "USD") }));
        var excessiveCommissionBps = Assert.Throws<BacktestValidationException>(() => BacktestRequestValidator.Validate(
            ValidRequest() with { CostModel = new BacktestCostModel(0m, BacktestValidationLimits.MaximumCommissionBps + 0.01m, "USD") }));
        var negativeSlippage = Assert.Throws<BacktestValidationException>(() => BacktestRequestValidator.Validate(
            ValidRequest() with { SlippageBps = -0.01m }));

        Assert.Equal(BacktestErrorCodes.InvalidCostModel, negativeCommission.Code);
        Assert.Equal(BacktestErrorCodes.InvalidCostModel, excessiveCommissionBps.Code);
        Assert.Equal(BacktestErrorCodes.InvalidSlippage, negativeSlippage.Code);
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
            Parameters: parameters,
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
