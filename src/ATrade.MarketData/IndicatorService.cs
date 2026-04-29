namespace ATrade.MarketData;

public sealed class IndicatorService
{
    private const int FastEmaPeriod = 12;
    private const int SlowEmaPeriod = 26;
    private const int SignalEmaPeriod = 9;
    private const int RsiPeriod = 14;

    public IndicatorResponse Calculate(string symbol, string timeframe, IReadOnlyList<OhlcvCandle> candles)
    {
        var movingAverages = new List<MovingAveragePoint>(candles.Count);
        var rsi = new List<RsiPoint>(candles.Count);
        var macd = new List<MacdPoint>(candles.Count);

        decimal fastEma = candles.Count > 0 ? candles[0].Close : 0m;
        decimal slowEma = fastEma;
        decimal signalEma = 0m;

        for (var index = 0; index < candles.Count; index++)
        {
            var candle = candles[index];
            movingAverages.Add(new MovingAveragePoint(
                candle.Time,
                Round(AverageClose(candles, index, 20)),
                Round(AverageClose(candles, index, 50))));

            rsi.Add(new RsiPoint(candle.Time, Round(CalculateRsi(candles, index))));

            if (index == 0)
            {
                fastEma = candle.Close;
                slowEma = candle.Close;
            }
            else
            {
                fastEma = CalculateEma(candle.Close, fastEma, FastEmaPeriod);
                slowEma = CalculateEma(candle.Close, slowEma, SlowEmaPeriod);
            }

            var macdValue = fastEma - slowEma;
            signalEma = index == 0 ? macdValue : CalculateEma(macdValue, signalEma, SignalEmaPeriod);
            macd.Add(new MacdPoint(
                candle.Time,
                Round(macdValue),
                Round(signalEma),
                Round(macdValue - signalEma)));
        }

        return new IndicatorResponse(symbol, timeframe, movingAverages, rsi, macd);
    }

    private static decimal AverageClose(IReadOnlyList<OhlcvCandle> candles, int index, int window)
    {
        var start = Math.Max(0, index - window + 1);
        var count = index - start + 1;
        var sum = 0m;

        for (var i = start; i <= index; i++)
        {
            sum += candles[i].Close;
        }

        return sum / count;
    }

    private static decimal CalculateRsi(IReadOnlyList<OhlcvCandle> candles, int index)
    {
        if (index == 0)
        {
            return 50m;
        }

        var start = Math.Max(1, index - RsiPeriod + 1);
        var gain = 0m;
        var loss = 0m;

        for (var i = start; i <= index; i++)
        {
            var change = candles[i].Close - candles[i - 1].Close;
            if (change >= 0m)
            {
                gain += change;
            }
            else
            {
                loss += Math.Abs(change);
            }
        }

        if (loss == 0m)
        {
            return 100m;
        }

        var relativeStrength = gain / loss;
        return 100m - (100m / (1m + relativeStrength));
    }

    private static decimal CalculateEma(decimal current, decimal previousEma, int period)
    {
        var multiplier = 2m / (period + 1m);
        return ((current - previousEma) * multiplier) + previousEma;
    }

    private static decimal Round(decimal value) => Math.Round(value, 4, MidpointRounding.AwayFromZero);
}
