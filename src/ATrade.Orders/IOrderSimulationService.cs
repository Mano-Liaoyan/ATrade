namespace ATrade.Orders;

public interface IOrderSimulationService
{
    OrderSimulationResult Simulate(OrderSimulationRequest request);
}
