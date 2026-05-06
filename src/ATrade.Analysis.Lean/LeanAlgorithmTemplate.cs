using System.Globalization;
using System.Text.Json;

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
        var strategyId = EscapePythonString(input.StrategyId);
        var parametersJson = EscapePythonString(JsonSerializer.Serialize(input.StrategyParameters));
        var initialCapital = input.InitialCapital.ToString(CultureInfo.InvariantCulture);
        var commissionPerTrade = input.CommissionPerTrade.ToString(CultureInfo.InvariantCulture);
        var commissionBps = input.CommissionBps.ToString(CultureInfo.InvariantCulture);
        var slippageBps = input.SlippageBps.ToString(CultureInfo.InvariantCulture);
        var currency = EscapePythonString(input.Currency);

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
        self.SetCash({{initialCapital}})
        self.strategy_id = "{{strategyId}}"
        self.strategy_parameters = json.loads("{{parametersJson}}")
        self.initial_capital = float({{initialCapital}})
        self.commission_per_trade = float({{commissionPerTrade}})
        self.commission_bps = float({{commissionBps}})
        self.slippage_bps = float({{slippageBps}})
        self.analysis_result = self._analyze_atrade_bars()

    def OnEndOfAlgorithm(self):
        self.Debug("{{ResultMarker}}" + json.dumps(self.analysis_result, separators=(",", ":")))

    def _analyze_atrade_bars(self):
        bars = self._read_bars()
        simulation = self._simulate_strategy(bars)
        summary = simulation["summary"]
        metrics = [
            { "name": "total-return", "value": round(summary["totalReturnPercent"], 4), "unit": "percent" },
            { "name": "max-drawdown", "value": round(summary["maxDrawdownPercent"], 4), "unit": "percent" },
            { "name": "signal-count", "value": len(simulation["signals"]), "unit": "count" },
            { "name": "trade-count", "value": summary["tradeCount"], "unit": "count" },
            { "name": "total-cost", "value": round(summary["totalCost"], 4), "unit": "{{currency}}" }
        ]

        return {
            "status": "completed",
            "engine": "lean",
            "symbol": "{{symbol}}",
            "timeframe": "{{timeframe}}",
            "strategyId": self.strategy_id,
            "parameters": self.strategy_parameters,
            "generatedAtUtc": self.Time.isoformat() + "Z",
            "signals": simulation["signals"],
            "metrics": metrics,
            "backtest": summary,
            "equityCurve": simulation["equityCurve"],
            "trades": simulation["trades"],
            "accounting": {
                "commissionPerTrade": self.commission_per_trade,
                "commissionBps": self.commission_bps,
                "slippageBps": self.slippage_bps,
                "currency": "{{currency}}"
            }
        }

    def _simulate_strategy(self, bars):
        cash = self.initial_capital
        quantity = 0.0
        entry = None
        trades = []
        signals = []
        equity_curve = []
        peak_equity = self.initial_capital
        total_cost = 0.0
        wins = 0
        completed_trades = 0

        for index, bar in enumerate(bars):
            action = self._strategy_action(bars, index, quantity > 0)
            if action is not None and action["action"] == "enter" and quantity <= 0:
                entry_result = self._enter_position(bar, cash, action)
                if entry_result is not None:
                    cash = entry_result["cash"]
                    quantity = entry_result["quantity"]
                    entry = entry_result["entry"]
                    total_cost += entry_result["cost"]
                    signals.append(entry_result["signal"])
            elif action is not None and action["action"] == "exit" and quantity > 0 and entry is not None:
                exit_result = self._exit_position(bar, cash, quantity, entry, action["rationale"], "strategy-exit")
                cash = exit_result["cash"]
                quantity = 0.0
                entry = None
                total_cost += exit_result["cost"]
                trades.append(exit_result["trade"])
                signals.append(exit_result["signal"])
                completed_trades += 1
                if exit_result["trade"]["netPnl"] > 0:
                    wins += 1

            equity = cash + (quantity * bar["close"])
            peak_equity = max(peak_equity, equity)
            drawdown = 0.0 if peak_equity <= 0 else max(0.0, ((peak_equity - equity) / peak_equity) * 100.0)
            equity_curve.append({
                "time": bar["time"],
                "equity": round(equity, 4),
                "drawdownPercent": round(drawdown, 4)
            })

        if quantity > 0 and entry is not None:
            exit_result = self._exit_position(bars[-1], cash, quantity, entry, "Closed open analysis position at the end of the server-side bar window.", "end-of-window")
            cash = exit_result["cash"]
            total_cost += exit_result["cost"]
            trades.append(exit_result["trade"])
            signals.append(exit_result["signal"])
            completed_trades += 1
            if exit_result["trade"]["netPnl"] > 0:
                wins += 1
            peak_equity = max(peak_equity, cash)
            final_drawdown = 0.0 if peak_equity <= 0 else max(0.0, ((peak_equity - cash) / peak_equity) * 100.0)
            equity_curve[-1] = {
                "time": bars[-1]["time"],
                "equity": round(cash, 4),
                "drawdownPercent": round(final_drawdown, 4)
            }

        final_equity = cash
        total_return = 0.0 if self.initial_capital <= 0 else ((final_equity / self.initial_capital) - 1.0) * 100.0
        max_drawdown = max([point["drawdownPercent"] for point in equity_curve]) if len(equity_curve) > 0 else 0.0
        win_rate = 0.0 if completed_trades == 0 else (wins / completed_trades) * 100.0

        return {
            "signals": signals,
            "trades": trades,
            "equityCurve": equity_curve,
            "summary": {
                "startUtc": bars[0]["time"],
                "endUtc": bars[-1]["time"],
                "initialCapital": round(self.initial_capital, 2),
                "finalEquity": round(final_equity, 2),
                "totalReturnPercent": round(total_return, 4),
                "tradeCount": completed_trades,
                "winRatePercent": round(win_rate, 4),
                "maxDrawdownPercent": round(max_drawdown, 4),
                "totalCost": round(total_cost, 4)
            }
        }

    def _enter_position(self, bar, cash, action):
        execution_price = bar["close"] * (1.0 + (self.slippage_bps / 10000.0))
        available = max(0.0, cash - self.commission_per_trade)
        if available <= 0 or execution_price <= 0:
            return None
        quantity = available / (execution_price * (1.0 + (self.commission_bps / 10000.0)))
        gross_value = quantity * execution_price
        commission = self.commission_per_trade + (gross_value * (self.commission_bps / 10000.0))
        next_cash = cash - gross_value - commission
        slippage_cost = quantity * abs(execution_price - bar["close"])
        cost = commission + slippage_cost
        return {
            "cash": next_cash,
            "quantity": quantity,
            "cost": cost,
            "entry": {
                "time": bar["time"],
                "price": execution_price,
                "quantity": quantity,
                "cashBefore": cash,
                "cost": cost
            },
            "signal": self._signal(bar, action["kind"], "long", action["confidence"], action["rationale"], execution_price)
        }

    def _exit_position(self, bar, cash, quantity, entry, rationale, exit_reason):
        execution_price = bar["close"] * (1.0 - (self.slippage_bps / 10000.0))
        gross_value = quantity * execution_price
        commission = self.commission_per_trade + (gross_value * (self.commission_bps / 10000.0))
        next_cash = cash + gross_value - commission
        slippage_cost = quantity * abs(bar["close"] - execution_price)
        exit_cost = commission + slippage_cost
        total_trade_cost = entry["cost"] + exit_cost
        gross_pnl = (execution_price - entry["price"]) * quantity
        net_pnl = next_cash - entry["cashBefore"]
        return_percent = 0.0 if entry["cashBefore"] == 0 else (net_pnl / entry["cashBefore"]) * 100.0
        return {
            "cash": next_cash,
            "cost": exit_cost,
            "trade": {
                "entryTime": entry["time"],
                "exitTime": bar["time"],
                "direction": "long",
                "entryPrice": round(entry["price"], 6),
                "exitPrice": round(execution_price, 6),
                "quantity": round(quantity, 8),
                "grossPnl": round(gross_pnl, 4),
                "netPnl": round(net_pnl, 4),
                "returnPercent": round(return_percent, 4),
                "totalCost": round(total_trade_cost, 4),
                "exitReason": exit_reason
            },
            "signal": self._signal(bar, self._strategy_kind(), "flat", 0.65, rationale, execution_price)
        }

    def _strategy_action(self, bars, index, invested):
        if self.strategy_id == "rsi-mean-reversion":
            return self._rsi_action(bars, index, invested)
        if self.strategy_id == "breakout":
            return self._breakout_action(bars, index, invested)
        return self._sma_action(bars, index, invested)

    def _sma_action(self, bars, index, invested):
        short_window = self._int_parameter("shortWindow", 20)
        long_window = self._int_parameter("longWindow", 50)
        if index + 1 < long_window or index == 0:
            return None
        closes = [bar["close"] for bar in bars]
        current_spread = self._sma(closes, index, short_window) - self._sma(closes, index, long_window)
        previous_spread = self._sma(closes, index - 1, short_window) - self._sma(closes, index - 1, long_window)
        if not invested and previous_spread <= 0 and current_spread > 0:
            return { "action": "enter", "kind": self._strategy_kind(), "confidence": 0.72, "rationale": "Short SMA crossed above long SMA in the LEAN analysis run." }
        if invested and previous_spread >= 0 and current_spread < 0:
            return { "action": "exit", "kind": self._strategy_kind(), "confidence": 0.68, "rationale": "Short SMA crossed below long SMA in the LEAN analysis run." }
        return None

    def _rsi_action(self, bars, index, invested):
        period = self._int_parameter("rsiPeriod", 14)
        oversold = self._float_parameter("oversoldThreshold", 30.0)
        overbought = self._float_parameter("overboughtThreshold", 70.0)
        if index < period:
            return None
        rsi = self._rsi([bar["close"] for bar in bars], index, period)
        if not invested and rsi <= oversold:
            return { "action": "enter", "kind": self._strategy_kind(), "confidence": 0.7, "rationale": "RSI moved into the configured oversold zone in the LEAN analysis run." }
        if invested and rsi >= overbought:
            return { "action": "exit", "kind": self._strategy_kind(), "confidence": 0.67, "rationale": "RSI moved into the configured overbought zone in the LEAN analysis run." }
        return None

    def _breakout_action(self, bars, index, invested):
        lookback = self._int_parameter("lookbackWindow", 20)
        if index < lookback:
            return None
        prior_bars = bars[index - lookback:index]
        breakout_level = max([bar["high"] for bar in prior_bars])
        breakdown_level = min([bar["low"] for bar in prior_bars])
        close = bars[index]["close"]
        if not invested and close > breakout_level:
            return { "action": "enter", "kind": self._strategy_kind(), "confidence": 0.69, "rationale": "Close broke above the configured prior high window in the LEAN analysis run." }
        if invested and close < breakdown_level:
            return { "action": "exit", "kind": self._strategy_kind(), "confidence": 0.66, "rationale": "Close broke below the configured prior low window in the LEAN analysis run." }
        return None

    def _sma(self, closes, index, window):
        start = max(0, index + 1 - window)
        values = closes[start:index + 1]
        return sum(values) / len(values)

    def _rsi(self, closes, index, period):
        gains = []
        losses = []
        for item_index in range(index - period + 1, index + 1):
            change = closes[item_index] - closes[item_index - 1]
            if change >= 0:
                gains.append(change)
                losses.append(0.0)
            else:
                gains.append(0.0)
                losses.append(abs(change))
        average_gain = sum(gains) / period
        average_loss = sum(losses) / period
        if average_loss == 0:
            return 100.0
        relative_strength = average_gain / average_loss
        return 100.0 - (100.0 / (1.0 + relative_strength))

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

    def _signal(self, bar, kind, direction, confidence, rationale, price):
        return {
            "time": bar["time"],
            "kind": kind,
            "direction": direction,
            "confidence": confidence,
            "rationale": rationale,
            "price": round(price, 6)
        }

    def _strategy_kind(self):
        if self.strategy_id == "rsi-mean-reversion":
            return "rsi-mean-reversion"
        if self.strategy_id == "breakout":
            return "breakout"
        return "moving-average-crossover"

    def _int_parameter(self, name, fallback):
        return int(self.strategy_parameters.get(name, fallback))

    def _float_parameter(self, name, fallback):
        return float(self.strategy_parameters.get(name, fallback))
""";

        LeanAnalysisGuardrails.EnsureAnalysisOnly(algorithm);
        return algorithm;
    }

    private static string EscapePythonString(string value) => value.Replace("\\", "\\\\", StringComparison.Ordinal).Replace("\"", "\\\"", StringComparison.Ordinal);
}
