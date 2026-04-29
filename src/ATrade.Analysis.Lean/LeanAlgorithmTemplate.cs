using System.Globalization;

namespace ATrade.Analysis.Lean;

public static class LeanAlgorithmTemplate
{
    public const string ResultMarker = "ATRADE_ANALYSIS_RESULT:";

    public static string Create(LeanInputData input)
    {
        ArgumentNullException.ThrowIfNull(input);

        var start = input.StartUtc.UtcDateTime;
        var end = input.EndUtc.UtcDateTime;
        var symbol = EscapePythonString(input.Symbol.Symbol);
        var timeframe = EscapePythonString(input.Timeframe);

        var algorithm = $$"""
from AlgorithmImports import *
import csv
import json
import math
import os

class ATradeLeanAnalysisAlgorithm(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate({{start.Year.ToString(CultureInfo.InvariantCulture)}}, {{start.Month.ToString(CultureInfo.InvariantCulture)}}, {{start.Day.ToString(CultureInfo.InvariantCulture)}})
        self.SetEndDate({{end.Year.ToString(CultureInfo.InvariantCulture)}}, {{end.Month.ToString(CultureInfo.InvariantCulture)}}, {{end.Day.ToString(CultureInfo.InvariantCulture)}})
        self.SetCash(100000)
        self.analysis_result = self._analyze_atrade_bars()

    def OnEndOfAlgorithm(self):
        self.Debug("{{ResultMarker}}" + json.dumps(self.analysis_result, separators=(",", ":")))

    def _analyze_atrade_bars(self):
        bars = self._read_bars()
        closes = [bar["close"] for bar in bars]
        signals = []
        short_window = 5
        long_window = 20
        previous_spread = None

        for index in range(len(bars)):
            if index + 1 < long_window:
                continue

            short_average = sum(closes[index + 1 - short_window:index + 1]) / short_window
            long_average = sum(closes[index + 1 - long_window:index + 1]) / long_window
            spread = short_average - long_average

            if previous_spread is not None and previous_spread <= 0 and spread > 0:
                signals.append(self._signal(bars[index], "bullish", 0.72, "Fast SMA crossed above slow SMA in the LEAN analysis run."))
            elif previous_spread is not None and previous_spread >= 0 and spread < 0:
                signals.append(self._signal(bars[index], "bearish", 0.68, "Fast SMA crossed below slow SMA in the LEAN analysis run."))

            previous_spread = spread

        total_return = 0.0
        if len(closes) >= 2 and closes[0] != 0:
            total_return = ((closes[-1] / closes[0]) - 1.0) * 100.0

        max_drawdown = self._max_drawdown_percent(closes)
        final_equity = 100000.0 * (1.0 + (total_return / 100.0))

        return {
            "status": "completed",
            "engine": "lean",
            "symbol": "{{symbol}}",
            "timeframe": "{{timeframe}}",
            "generatedAtUtc": self.Time.isoformat() + "Z",
            "signals": signals,
            "metrics": [
                { "name": "total-return", "value": round(total_return, 4), "unit": "percent" },
                { "name": "max-drawdown", "value": round(max_drawdown, 4), "unit": "percent" },
                { "name": "signal-count", "value": len(signals), "unit": "count" }
            ],
            "backtest": {
                "startUtc": bars[0]["time"],
                "endUtc": bars[-1]["time"],
                "initialCapital": 100000.0,
                "finalEquity": round(final_equity, 2),
                "totalReturnPercent": round(total_return, 4),
                "tradeCount": len(signals),
                "winRatePercent": self._win_rate_percent(signals)
            }
        }

    def _read_bars(self):
        path = os.path.join(os.path.dirname(__file__), "{{LeanInputConverter.BarsFileName}}")
        bars = []
        with open(path, newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                bars.append({
                    "time": row["time"],
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": int(row["volume"])
                })
        return bars

    def _signal(self, bar, direction, confidence, rationale):
        return {
            "time": bar["time"],
            "kind": "moving-average-crossover",
            "direction": direction,
            "confidence": confidence,
            "rationale": rationale
        }

    def _max_drawdown_percent(self, closes):
        peak = 0.0
        drawdown = 0.0
        for close in closes:
            peak = max(peak, close)
            if peak > 0:
                drawdown = min(drawdown, ((close / peak) - 1.0) * 100.0)
        return abs(drawdown)

    def _win_rate_percent(self, signals):
        if len(signals) == 0:
            return 0.0
        bullish = len([signal for signal in signals if signal["direction"] == "bullish"])
        return round((bullish / len(signals)) * 100.0, 4)
""";

        LeanAnalysisGuardrails.EnsureAnalysisOnly(algorithm);
        return algorithm;
    }

    private static string EscapePythonString(string value) => value.Replace("\\", "\\\\", StringComparison.Ordinal).Replace("\"", "\\\"", StringComparison.Ordinal);
}
