using Microsoft.AspNetCore.SignalR;

namespace ATrade.MarketData;

public sealed class MarketDataHub(IMarketDataStreamingService streamingService) : Hub
{
    public async Task Subscribe(string symbol, string timeframe)
    {
        if (!streamingService.TryCreateSnapshot(symbol, timeframe, out var update, out var error) || update is null)
        {
            throw new HubException(error?.Message ?? "Unable to create mocked market-data update.");
        }

        await Groups.AddToGroupAsync(Context.ConnectionId, streamingService.GetGroupName(update.Symbol, update.Timeframe));
        await Clients.Caller.SendAsync("marketDataUpdated", update);
    }

    public async Task Unsubscribe(string symbol, string timeframe)
    {
        await Groups.RemoveFromGroupAsync(Context.ConnectionId, streamingService.GetGroupName(symbol, timeframe));
    }
}
