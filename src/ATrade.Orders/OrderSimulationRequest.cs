namespace ATrade.Orders;

public sealed record OrderSimulationRequest(
    string Symbol,
    string Side,
    decimal Quantity,
    string OrderType,
    decimal? LimitPrice);
