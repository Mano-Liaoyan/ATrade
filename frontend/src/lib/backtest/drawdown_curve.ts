// The drawdown curve of a test: at each equity point, the fall from the highest equity so far, as a negative percent.
// The highest equity starts at the start capital, like the max drawdown metric of the backend
// (backend/src/atrade/backtest/backtest_metrics.py), so the lowest point of the curve is the max drawdown.

export interface DrawdownPoint {
  timeUtc: string;
  drawdownPercent: number;
}

const PERCENT = 100;

export function computeDrawdownCurve(
  points: readonly { time_utc: string; equity_usd: string }[],
  startCapitalUsd: string | null,
): DrawdownPoint[] {
  let highestEquity = startCapitalUsd === null ? 0 : Number(startCapitalUsd);
  return points.map((point) => {
    const equity = Number(point.equity_usd);
    highestEquity = Math.max(highestEquity, equity);
    const drawdownPercent = highestEquity > 0 ? ((equity - highestEquity) / highestEquity) * PERCENT : 0;
    // 0 - 0 gives -0; the curve has 0 at the highest equity.
    return { timeUtc: point.time_utc, drawdownPercent: drawdownPercent === 0 ? 0 : drawdownPercent };
  });
}
