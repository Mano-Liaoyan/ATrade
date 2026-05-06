using System.Globalization;
using System.Text;
using System.Text.Json;
using ATrade.Analysis;
using ATrade.MarketData;

namespace ATrade.Analysis.Lean;

public sealed record LeanInputData(
    MarketDataSymbolIdentity Symbol,
    string Timeframe,
    DateTimeOffset StartUtc,
    DateTimeOffset EndUtc,
    IReadOnlyList<LeanInputBar> Bars,
    string StrategyId,
    IReadOnlyDictionary<string, JsonElement> StrategyParameters,
    decimal InitialCapital,
    decimal CommissionPerTrade,
    decimal CommissionBps,
    decimal SlippageBps,
    string Currency);

public sealed record LeanInputBar(
    DateTimeOffset TimeUtc,
    decimal Open,
    decimal High,
    decimal Low,
    decimal Close,
    long Volume);

public static class LeanInputConverter
{
    public const string BarsFileName = "atrade-bars.csv";

    public static LeanInputData FromRequest(AnalysisRequest request)
    {
        ArgumentNullException.ThrowIfNull(request);

        if (request.Bars.Count == 0)
        {
            throw new LeanInputConversionException("At least one normalized OHLCV bar is required for LEAN analysis.");
        }

        var bars = request.Bars
            .Select(ToLeanBar)
            .OrderBy(bar => bar.TimeUtc)
            .ToArray();

        var backtestSettings = request.BacktestSettings ?? new AnalysisBacktestSettings(
            InitialCapital: 100_000m,
            CommissionPerTrade: 0m,
            CommissionBps: 0m,
            SlippageBps: 0m,
            Currency: "USD");

        return new LeanInputData(
            request.Symbol,
            string.IsNullOrWhiteSpace(request.Timeframe) ? MarketDataTimeframes.OneDay : request.Timeframe.Trim(),
            bars[0].TimeUtc,
            bars[^1].TimeUtc,
            bars,
            NormalizeStrategyId(request.StrategyName),
            NormalizeStrategyParameters(request.StrategyParameters),
            decimal.Round(backtestSettings.InitialCapital, 2, MidpointRounding.AwayFromZero),
            decimal.Round(backtestSettings.CommissionPerTrade, 4, MidpointRounding.AwayFromZero),
            decimal.Round(backtestSettings.CommissionBps, 4, MidpointRounding.AwayFromZero),
            decimal.Round(backtestSettings.SlippageBps, 4, MidpointRounding.AwayFromZero),
            string.IsNullOrWhiteSpace(backtestSettings.Currency) ? "USD" : backtestSettings.Currency.Trim().ToUpperInvariant());
    }

    public static string ToCsv(LeanInputData input)
    {
        ArgumentNullException.ThrowIfNull(input);

        var builder = new StringBuilder();
        builder.AppendLine("time,open,high,low,close,volume");

        foreach (var bar in input.Bars)
        {
            builder
                .Append(bar.TimeUtc.ToString("O", CultureInfo.InvariantCulture)).Append(',')
                .Append(bar.Open.ToString(CultureInfo.InvariantCulture)).Append(',')
                .Append(bar.High.ToString(CultureInfo.InvariantCulture)).Append(',')
                .Append(bar.Low.ToString(CultureInfo.InvariantCulture)).Append(',')
                .Append(bar.Close.ToString(CultureInfo.InvariantCulture)).Append(',')
                .Append(bar.Volume.ToString(CultureInfo.InvariantCulture))
                .AppendLine();
        }

        return builder.ToString();
    }

    private static string NormalizeStrategyId(string? strategyName)
    {
        if (string.IsNullOrWhiteSpace(strategyName))
        {
            return "sma-crossover";
        }

        var normalized = strategyName.Trim().ToLowerInvariant();
        return normalized switch
        {
            "sma-crossover" or "rsi-mean-reversion" or "breakout" => normalized,
            _ => "sma-crossover",
        };
    }

    private static IReadOnlyDictionary<string, JsonElement> NormalizeStrategyParameters(IReadOnlyDictionary<string, JsonElement>? parameters)
    {
        if (parameters is null || parameters.Count == 0)
        {
            return new Dictionary<string, JsonElement>(StringComparer.Ordinal);
        }

        return parameters.ToDictionary(
            parameter => parameter.Key,
            parameter => parameter.Value.Clone(),
            StringComparer.Ordinal);
    }

    private static LeanInputBar ToLeanBar(OhlcvCandle candle)
    {
        if (candle.Volume < 0)
        {
            throw new LeanInputConversionException("LEAN analysis cannot run over bars with negative volume.");
        }

        if (candle.High < candle.Low)
        {
            throw new LeanInputConversionException("LEAN analysis cannot run over bars whose high is below their low.");
        }

        if (candle.Open <= 0 || candle.High <= 0 || candle.Low <= 0 || candle.Close <= 0)
        {
            throw new LeanInputConversionException("LEAN analysis requires positive OHLC prices.");
        }

        return new LeanInputBar(candle.Time.ToUniversalTime(), candle.Open, candle.High, candle.Low, candle.Close, candle.Volume);
    }
}

public sealed class LeanInputConversionException(string message) : Exception(message);
