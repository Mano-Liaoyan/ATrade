// The trade marks of the bar chart of a backtest or a forward test (docs/architecture/indicator.md section 23.9.9):
// the pure functions (trade to bar, one mark for each bar and side, the merge at a small bar spacing, the place of each
// mark, the tooltip lines) and the series primitive that draws the marks on the candlestick series.
import type {
  IChartApi,
  IPrimitivePaneRenderer,
  IPrimitivePaneView,
  ISeriesApi,
  ISeriesPrimitive,
  Logical,
  LogicalRange,
  SeriesAttachedParameter,
  UTCTimestamp,
} from 'lightweight-charts';
import type { components } from '#lib/api';
import { formatAmount } from '#lib/foundation/value_format';
import type { BarPeriod } from './bars';
import type { Instrument } from './instrument_search';

/** A row of the backtest Trades tab or of the forward test Fills tab. */
export type TradeRecord =
  | components['schemas']['TradeResponse']
  | components['schemas']['ForwardTestFillResponse'];

export type TradeSide = 'BUY' | 'SELL';

/** One trade or fill of the run, with its time in UNIX seconds. Decimal values are API text. */
export interface ChartTrade {
  time: number;
  side: TradeSide;
  quantity: string;
  price: string;
  /** The net profit of the round trip that the trade ends, after commissions, else null. */
  roundTripNetProfit: string | null;
}

/** The trades of one bar and side. `tradeIndexes` point into the trade list of the chart. */
export interface TradeMark {
  barIndex: number;
  side: TradeSide;
  tradeIndexes: number[];
}

/** The place of a mark in pane pixels: the pointer tip at `pointerY`, the 16px square from `squareTop`. */
export interface TradeMarkBox {
  mark: TradeMark;
  x: number;
  pointerY: number;
  squareTop: number;
}

export interface TradeLine {
  text: string;
  profit: { text: string; kind: 'success' | 'error' } | null;
}

export const MARK_SIZE = 16;
const MARK_GAP = 4;
const POINTER_HEIGHT = 4;
const RING_WIDTH = 2;
const HALF = 0.5;
const MILLISECONDS_PER_SECOND = 1000;
// The text baseline "middle" is a little high for capitals.
const TEXT_OFFSET = 0.5;

export const BAR_PERIOD_SECONDS: Record<BarPeriod, number> = {
  '1-MINUTE': 60,
  '5-MINUTE': 300,
  '15-MINUTE': 900,
  '30-MINUTE': 1800,
  '1-HOUR': 3600,
  '1-DAY': 86_400,
};

/** The bar with start < `tradeTime` ≤ start + bar period, else -1. A backtest fill at an open is at bar start + 1 ms. */
export function findTradeBarIndex(
  barTimes: readonly number[],
  periodSeconds: number,
  tradeTime: number,
): number {
  // The last bar that starts before the trade.
  let low = 0;
  let high = barTimes.length - 1;
  let found = -1;
  while (low <= high) {
    const middle = Math.floor((low + high) * HALF);
    if ((barTimes[middle] ?? Infinity) < tradeTime) {
      found = middle;
      low = middle + 1;
    } else {
      high = middle - 1;
    }
  }
  if (found === -1 || tradeTime > (barTimes[found] ?? 0) + periodSeconds) {
    return -1;
  }
  return found;
}

/** The chart trades of the table rows, and the chart trade of each row (null for a split adjustment: no mark). */
export function listChartTrades(
  records: readonly TradeRecord[],
  member?: Pick<Instrument, 'symbol' | 'exchange'>,
): {
  trades: ChartTrade[];
  tradeIndexByRow: (number | null)[];
} {
  const trades: ChartTrade[] = [];
  const tradeIndexByRow = records.map((record) => {
    if (('kind' in record && record.kind !== 'fill') || record.price_usd === null) {
      return null;
    }
    if (member !== undefined && (record.symbol !== member.symbol || record.exchange !== member.exchange)) {
      return null;
    }
    trades.push({
      time: Date.parse(record.time_utc) / MILLISECONDS_PER_SECOND,
      side: record.side,
      quantity: record.quantity_shares,
      price: record.price_usd,
      roundTripNetProfit: record.round_trip_net_profit_usd,
    });
    return trades.length - 1;
  });
  return { trades, tradeIndexByRow };
}

/** One mark for each bar and side, by bar, the buy mark first. A trade outside the bars has no mark. */
export function groupTradeMarks(
  trades: readonly ChartTrade[],
  barTimes: readonly number[],
  periodSeconds: number,
): TradeMark[] {
  const marks = new Map<string, TradeMark>();
  trades.forEach((trade, tradeIndex) => {
    const barIndex = findTradeBarIndex(barTimes, periodSeconds, trade.time);
    if (barIndex === -1) {
      return;
    }
    const key = `${String(barIndex)}:${trade.side}`;
    const mark = marks.get(key);
    if (mark === undefined) {
      marks.set(key, { barIndex, side: trade.side, tradeIndexes: [tradeIndex] });
    } else {
      mark.tradeIndexes.push(tradeIndex);
    }
  });
  return [...marks.values()].sort(
    (first, second) => (first.barIndex === second.barIndex ? (first.side === 'BUY' ? -1 : 1) : first.barIndex - second.barIndex),
  );
}

/** At a bar spacing below 16px, the marks of one side that touch the mark at the first bar become that mark. */
export function mergeTouchingMarks(marks: readonly TradeMark[], barSpacing: number): TradeMark[] {
  if (barSpacing >= MARK_SIZE) {
    return [...marks];
  }
  const merged: TradeMark[] = [];
  const lastBySide = new Map<TradeSide, TradeMark>();
  for (const mark of marks) {
    const last = lastBySide.get(mark.side);
    if (last !== undefined && (mark.barIndex - last.barIndex) * barSpacing < MARK_SIZE) {
      last.tradeIndexes.push(...mark.tradeIndexes);
      continue;
    }
    const copy = { ...mark, tradeIndexes: [...mark.tradeIndexes] };
    merged.push(copy);
    lastBySide.set(mark.side, copy);
  }
  return merged;
}

/** The place of each mark: the B mark 4px below the bar low, the S mark 4px above the bar high. */
export function layoutTradeMarks(
  marks: readonly TradeMark[],
  bars: readonly { low: number; high: number }[],
  toX: (barIndex: number) => number | null,
  toY: (price: number) => number | null,
): TradeMarkBox[] {
  const boxes: TradeMarkBox[] = [];
  for (const mark of marks) {
    const bar = bars[mark.barIndex];
    const x = toX(mark.barIndex);
    const y = bar === undefined ? null : toY(mark.side === 'BUY' ? bar.low : bar.high);
    if (x === null || y === null) {
      continue;
    }
    if (mark.side === 'BUY') {
      const pointerY = y + MARK_GAP;
      boxes.push({ mark, x, pointerY, squareTop: pointerY + POINTER_HEIGHT });
    } else {
      const pointerY = y - MARK_GAP;
      boxes.push({ mark, x, pointerY, squareTop: pointerY - POINTER_HEIGHT - MARK_SIZE });
    }
  }
  return boxes;
}

/** The bounds of the square and the pointer of a mark, and the center of the square. */
export function readMarkBounds(box: TradeMarkBox): { left: number; top: number; width: number; height: number; centerY: number } {
  const top = Math.min(box.pointerY, box.squareTop);
  return { left: box.x - MARK_SIZE * HALF, top, width: MARK_SIZE, height: MARK_SIZE + POINTER_HEIGHT, centerY: box.squareTop + MARK_SIZE * HALF };
}

export function findMarkAt(
  boxes: readonly TradeMarkBox[],
  x: number,
  y: number,
): TradeMarkBox | undefined {
  return boxes.find((box) => {
    const { left, top, width, height } = readMarkBounds(box);
    return x >= left && x <= left + width && y >= top && y <= top + height;
  });
}

/** "Buy 50 @ 182.35", or "Sell 50 @ 190.10" with "+387.50": the net profit of the round trip that the trade ends. */
export function formatTradeLine(trade: ChartTrade): TradeLine {
  const text = `${trade.side === 'BUY' ? 'Buy' : 'Sell'} ${trade.quantity} @ ${formatAmount(trade.price)}`;
  if (trade.roundTripNetProfit === null) {
    return { text, profit: null };
  }
  const profit = Number(trade.roundTripNetProfit);
  const amount = formatAmount(String(Math.abs(profit)));
  return profit < 0
    ? { text, profit: { text: `−${amount}`, kind: 'error' } }
    : { text, profit: { text: `+${amount}`, kind: 'success' } };
}

// The chart cannot scroll the first bar to the right of the left edge. A bar near the first bar is in the center of
// a narrower range, with at least this count of bars on each side.
const MIN_CENTERED_HALF_WIDTH = 10;

/** The visible range with the bar in its center: the same width, or narrower when the bar is near the first bar. */
export function readCenteredRange(range: { from: number; to: number }, barIndex: number): { from: number; to: number } {
  const halfWidth = Math.max(Math.min((range.to - range.from) * HALF, barIndex), MIN_CENTERED_HALF_WIDTH);
  return { from: barIndex - halfWidth, to: barIndex + halfWidth };
}

export function centerBar(chart: IChartApi, barIndex: number): void {
  const range = chart.timeScale().getVisibleLogicalRange();
  if (range !== null) {
    const centered = readCenteredRange(range, barIndex);
    chart
      .timeScale()
      .setVisibleLogicalRange({
        from: centered.from as Logical,
        to: centered.to as Logical,
      } satisfies LogicalRange);
  }
}

export interface TradeMarkColors {
  background: string;
  text: string;
  ring: string;
  font: string;
}

type DrawTarget = Parameters<IPrimitivePaneRenderer['draw']>[0];

function drawMark(
  context: CanvasRenderingContext2D,
  box: TradeMarkBox,
  colors: TradeMarkColors,
  hasRing: boolean,
): void {
  const left = box.x - MARK_SIZE * HALF;
  const squareBottom = box.squareTop + MARK_SIZE;
  const pointerBase = box.mark.side === 'BUY' ? box.squareTop : squareBottom;
  context.fillStyle = colors.background;
  context.fillRect(left, box.squareTop, MARK_SIZE, MARK_SIZE);
  context.beginPath();
  context.moveTo(box.x - POINTER_HEIGHT, pointerBase);
  context.lineTo(box.x, box.pointerY);
  context.lineTo(box.x + POINTER_HEIGHT, pointerBase);
  context.closePath();
  context.fill();
  context.fillStyle = colors.text;
  context.font = colors.font;
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  context.fillText(box.mark.side === 'BUY' ? 'B' : 'S', box.x, box.squareTop + MARK_SIZE * HALF + TEXT_OFFSET);
  if (hasRing) {
    context.strokeStyle = colors.ring;
    context.lineWidth = RING_WIDTH;
    context.strokeRect(
      left - RING_WIDTH * HALF,
      box.squareTop - RING_WIDTH * HALF,
      MARK_SIZE + RING_WIDTH,
      MARK_SIZE + RING_WIDTH,
    );
  }
}

/**
 * Draws the marks on the price pane (`attachPrimitive` on the candlestick series). The chart gives the marks, the bars,
 * the colors, and the trades with a focus ring; the primitive does the merge and the layout at each redraw and gives
 * the boxes to `onLayout`, for the pointer hit test and the tooltip.
 */
export class TradeMarksPrimitive implements ISeriesPrimitive {
  private attachedParameters: SeriesAttachedParameter | null = null;
  private marks: TradeMark[] = [];
  private bars: readonly { time: number; low: number; high: number }[] = [];
  private ringTradeIndexes = new Set<number>();
  private boxes: TradeMarkBox[] = [];
  private readonly view: IPrimitivePaneView;

  constructor(
    private colors: TradeMarkColors,
    private readonly onLayout: (boxes: TradeMarkBox[]) => void,
  ) {
    const renderer: IPrimitivePaneRenderer = {
      draw: (target: DrawTarget) => {
        target.useMediaCoordinateSpace(({ context }) => {
          for (const box of this.boxes) {
            drawMark(context, box, this.colors, this.hasRing(box));
          }
        });
      },
    };
    this.view = { renderer: () => renderer, zOrder: () => 'top' };
  }

  attached(parameters: SeriesAttachedParameter): void {
    this.attachedParameters = parameters;
  }

  detached(): void {
    this.attachedParameters = null;
  }

  setMarks(marks: TradeMark[], bars: readonly { time: number; low: number; high: number }[]): void {
    this.marks = marks;
    this.bars = bars;
    this.attachedParameters?.requestUpdate();
  }

  setRingTrades(tradeIndexes: readonly number[]): void {
    this.ringTradeIndexes = new Set(tradeIndexes);
    this.attachedParameters?.requestUpdate();
  }

  setColors(colors: TradeMarkColors): void {
    this.colors = colors;
    this.attachedParameters?.requestUpdate();
  }

  hasRing(box: TradeMarkBox): boolean {
    return box.mark.tradeIndexes.some((tradeIndex) => this.ringTradeIndexes.has(tradeIndex));
  }

  updateAllViews(): void {
    const parameters = this.attachedParameters;
    if (parameters === null) {
      return;
    }
    const timeScale = parameters.chart.timeScale();
    const series = parameters.series as ISeriesApi<'Candlestick'>;
    // The bar spacing now, after each zoom.
    const barSpacing =
      (timeScale.logicalToCoordinate(1 as Logical) ?? 0) -
      (timeScale.logicalToCoordinate(0 as Logical) ?? 0);
    const merged = mergeTouchingMarks(this.marks, barSpacing);
    this.boxes = layoutTradeMarks(
      merged,
      this.bars,
      (barIndex) => {
        const bar = this.bars[barIndex];
        return bar === undefined ? null : timeScale.timeToCoordinate(bar.time as UTCTimestamp);
      },
      (price) => series.priceToCoordinate(price),
    );
    this.onLayout(this.boxes);
  }

  paneViews(): readonly IPrimitivePaneView[] {
    return [this.view];
  }
}
