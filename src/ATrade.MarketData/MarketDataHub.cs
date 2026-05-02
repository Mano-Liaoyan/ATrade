using Microsoft.AspNetCore.SignalR;

namespace ATrade.MarketData;

public sealed class MarketDataHub(IMarketDataStreamingService streamingService) : Hub
{
    public async Task Subscribe(string symbol, string timeframe)
    {
        var result = await streamingService.CreateSnapshotAsync(symbol, timeframe, Context.ConnectionAborted);
        if (result.IsFailure || result.Value is null)
        {
            throw new HubException(result.Error?.Message ?? "Unable to create market-data update.");
        }

        var update = result.Value;
        await Groups.AddToGroupAsync(Context.ConnectionId, streamingService.GetGroupName(update.Symbol, update.Timeframe), Context.ConnectionAborted);
        await Clients.Caller.SendAsync("marketDataUpdated", update, Context.ConnectionAborted);
    }

    public async Task Unsubscribe(string symbol, string timeframe)
    {
        await Groups.RemoveFromGroupAsync(Context.ConnectionId, streamingService.GetGroupName(symbol, timeframe));
    }
}
