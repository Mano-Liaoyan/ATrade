using ATrade.Brokers.Ibkr;
using Microsoft.Extensions.Options;

namespace ATrade.Orders.Tests;

public sealed class OrderSimulationServiceTests
{
    [Fact]
    public void Simulate_ReturnsDeterministicResultsForRepeatedMarketOrders()
    {
        var service = CreateService(IbkrAccountMode.Paper);
        var request = new OrderSimulationRequest(
            Symbol: "MSFT",
            Side: "Buy",
            Quantity: 5,
            OrderType: "Market",
            LimitPrice: null);

        var first = service.Simulate(request);
        var second = service.Simulate(request);

        Assert.Equal(first, second);
        Assert.True(first.Simulated);
        Assert.False(first.BrokerOrderPlacementAttempted);
        Assert.Equal("paper", first.BrokerMode);
    }

    [Fact]
    public void Simulate_UsesProvidedLimitPriceWithoutBrokerPlacement()
    {
        var service = CreateService(IbkrAccountMode.Paper);
        var request = new OrderSimulationRequest(
            Symbol: "NVDA",
            Side: "Sell",
            Quantity: 2.5m,
            OrderType: "Limit",
            LimitPrice: 123.45m);

        var result = service.Simulate(request);

        Assert.Equal(123.45m, result.SimulatedFillPrice);
        Assert.Equal(123.45m, result.LimitPrice);
        Assert.False(result.BrokerOrderPlacementAttempted);
        Assert.Contains("without calling broker order endpoints", result.Message);
    }

    [Fact]
    public void Simulate_RejectsNonPaperMode()
    {
        var service = CreateService(IbkrAccountMode.Live);
        var request = new OrderSimulationRequest(
            Symbol: "AAPL",
            Side: "Buy",
            Quantity: 1,
            OrderType: "Market",
            LimitPrice: null);

        var exception = Assert.Throws<IbkrPaperTradingRequiredException>(() => service.Simulate(request));

        Assert.Contains("Only Paper is supported", exception.Message);
    }

    private static OrderSimulationService CreateService(IbkrAccountMode accountMode)
    {
        var options = Options.Create(
            new IbkrGatewayOptions
            {
                AccountMode = accountMode,
                IntegrationEnabled = true,
            });

        return new OrderSimulationService(new IbkrPaperTradingGuard(options));
    }
}
