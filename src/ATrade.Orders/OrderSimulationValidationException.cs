namespace ATrade.Orders;

public sealed class OrderSimulationValidationException(string message) : ArgumentException(message);
