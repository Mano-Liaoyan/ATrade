using ATrade.Brokers.Ibkr;

namespace ATrade.Orders;

public sealed class OrderSimulationService(IIbkrPaperTradingGuard paperTradingGuard) : IOrderSimulationService
{
    public OrderSimulationResult Simulate(OrderSimulationRequest request)
    {
        ArgumentNullException.ThrowIfNull(request);
        paperTradingGuard.EnsurePaperOnly();

        var normalizedSymbol = NormalizeRequiredText(request.Symbol, nameof(request.Symbol));
        var normalizedSide = NormalizeSide(request.Side);
        var normalizedOrderType = NormalizeOrderType(request.OrderType);

        if (request.Quantity <= 0)
        {
            throw new OrderSimulationValidationException("Quantity must be greater than zero for paper-order simulation.");
        }

        if (normalizedOrderType == "Limit" && request.LimitPrice is not > 0)
        {
            throw new OrderSimulationValidationException("Limit orders require a positive limit price for deterministic simulation.");
        }

        decimal? normalizedLimitPrice = normalizedOrderType == "Limit"
            ? decimal.Round(request.LimitPrice!.Value, 2, MidpointRounding.AwayFromZero)
            : null;
        var simulatedFillPrice = normalizedLimitPrice ?? CalculateDeterministicMarketPrice(normalizedSymbol);
        var simulationId = BuildSimulationId(normalizedSymbol, normalizedSide, request.Quantity, normalizedOrderType, normalizedLimitPrice);

        return new OrderSimulationResult(
            Module: "orders",
            SimulationId: simulationId,
            Status: "simulated-filled",
            Simulated: true,
            BrokerOrderPlacementAttempted: false,
            BrokerMode: "paper",
            Symbol: normalizedSymbol,
            Side: normalizedSide,
            Quantity: request.Quantity,
            OrderType: normalizedOrderType,
            LimitPrice: normalizedLimitPrice,
            SimulatedFillPrice: simulatedFillPrice,
            FilledQuantity: request.Quantity,
            RemainingQuantity: 0m,
            Message: $"Simulated {normalizedSide.ToLowerInvariant()} order for {normalizedSymbol} without calling broker order endpoints.");
    }

    private static string NormalizeRequiredText(string? value, string argumentName)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            throw new OrderSimulationValidationException($"{argumentName} is required for paper-order simulation.");
        }

        return value.Trim().ToUpperInvariant();
    }

    private static string NormalizeSide(string? value)
    {
        return value?.Trim().ToUpperInvariant() switch
        {
            "BUY" => "Buy",
            "SELL" => "Sell",
            _ => throw new OrderSimulationValidationException("Side must be either Buy or Sell for paper-order simulation."),
        };
    }

    private static string NormalizeOrderType(string? value)
    {
        return value?.Trim().ToUpperInvariant() switch
        {
            "MARKET" => "Market",
            "LIMIT" => "Limit",
            _ => throw new OrderSimulationValidationException("OrderType must be either Market or Limit for paper-order simulation."),
        };
    }

    private static decimal CalculateDeterministicMarketPrice(string symbol)
    {
        var seed = 0;
        foreach (var character in symbol)
        {
            seed = (seed * 31) + character;
        }

        return decimal.Round(((Math.Abs(seed) % 5000) / 100m) + 25m, 2, MidpointRounding.AwayFromZero);
    }

    private static string BuildSimulationId(string symbol, string side, decimal quantity, string orderType, decimal? limitPrice)
    {
        var normalizedKey = string.Join(
            '|',
            symbol,
            side,
            quantity.ToString("0.####", System.Globalization.CultureInfo.InvariantCulture),
            orderType,
            limitPrice?.ToString("0.####", System.Globalization.CultureInfo.InvariantCulture) ?? "market");

        var seed = 0;
        foreach (var character in normalizedKey)
        {
            seed = (seed * 31) + character;
        }

        return $"sim-{Math.Abs(seed):x8}";
    }
}
