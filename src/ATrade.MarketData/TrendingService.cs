namespace ATrade.MarketData;

public sealed class TrendingService
{
    public TrendingSymbol CreateTrendingSymbol(MarketDataSymbol symbol, IReadOnlyList<OhlcvCandle> candles)
    {
        var latest = candles[^1];
        var previous = candles[Math.Max(0, candles.Count - 25)];
        var averageVolume = candles.Skip(Math.Max(0, candles.Count - 30)).Average(candle => (decimal)candle.Volume);
        var averageRange = candles.Skip(Math.Max(0, candles.Count - 30)).Average(candle => candle.High - candle.Low);

        var volumeSpike = Clamp(latest.Volume / Math.Max(1m, averageVolume), 0m, 3m);
        var priceMomentum = Clamp((latest.Close - previous.Close) / previous.Close * 100m, -5m, 5m);
        var volatility = Clamp(averageRange / latest.Close * 100m, 0m, 5m);
        var newsSentimentPlaceholder = GetNewsSentimentPlaceholder(symbol.Symbol);

        var score = Round((volumeSpike * 22m) + ((priceMomentum + 5m) * 5m) + (volatility * 7m) + (newsSentimentPlaceholder * 10m));
        var factors = new TrendingFactorBreakdown(
            Round(volumeSpike),
            Round(priceMomentum),
            Round(volatility),
            Round(newsSentimentPlaceholder));

        return new TrendingSymbol(
            symbol.Symbol,
            symbol.Name,
            symbol.AssetClass,
            symbol.Exchange,
            symbol.Sector,
            latest.Close,
            Round((latest.Close - previous.Close) / previous.Close * 100m),
            score,
            factors,
            new[]
            {
                $"Volume is {Round(volumeSpike)}x the recent mocked baseline.",
                $"Price momentum is {Round(priceMomentum)}% over the mocked lookback window.",
                $"Volatility contribution is {Round(volatility)}% from deterministic OHLC ranges.",
                "News sentiment is a clearly labeled mocked placeholder; no external news provider is called.",
            });
    }

    private static decimal GetNewsSentimentPlaceholder(string symbol)
    {
        var bucket = StableHash(symbol) % 5;
        return bucket switch
        {
            0 => -0.1m,
            1 => 0m,
            2 => 0.1m,
            3 => 0.2m,
            _ => 0.3m,
        };
    }

    private static int StableHash(string value)
    {
        var hash = 17;
        foreach (var character in value.ToUpperInvariant())
        {
            hash = unchecked((hash * 31) + character);
        }

        return Math.Abs(hash % 10_000);
    }

    private static decimal Clamp(decimal value, decimal min, decimal max) => Math.Min(max, Math.Max(min, value));

    private static decimal Round(decimal value) => Math.Round(value, 4, MidpointRounding.AwayFromZero);
}
