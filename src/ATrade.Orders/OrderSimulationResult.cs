namespace ATrade.Orders;

public sealed record OrderSimulationResult(
    string Module,
    string SimulationId,
    string Status,
    bool Simulated,
    bool BrokerOrderPlacementAttempted,
    string BrokerMode,
    string Symbol,
    string Side,
    decimal Quantity,
    string OrderType,
    decimal? LimitPrice,
    decimal SimulatedFillPrice,
    decimal FilledQuantity,
    decimal RemainingQuantity,
    string Message);
