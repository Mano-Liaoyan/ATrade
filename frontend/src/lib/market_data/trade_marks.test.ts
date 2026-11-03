import { describe, expect, it } from 'vite-plus/test';
import {
  findMarkAt,
  findTradeBarIndex,
  formatTradeLine,
  groupTradeMarks,
  layoutTradeMarks,
  listChartTrades,
  mergeTouchingMarks,
  readCenteredRange,
  type ChartTrade,
  type TradeMark,
} from './trade_marks';

const DAY = 86_400;
// 5 daily bars from 2025-11-03.
const FIRST_BAR = Date.UTC(2025, 10, 3) / 1000;
const BAR_TIMES = [0, 1, 2, 3, 4].map((day) => FIRST_BAR + day * DAY);

function makeTrade(
  time: number,
  side: 'BUY' | 'SELL',
  roundTripNetProfit: string | null = null,
): ChartTrade {
  return { time, side, quantity: '50', price: '182.35', roundTripNetProfit };
}

describe('findTradeBarIndex', () => {
  it('puts a trade at the bar end on that bar', () => {
    expect(findTradeBarIndex(BAR_TIMES, DAY, FIRST_BAR + DAY)).toBe(0);
  });

  it('puts a trade after the bar start on that bar', () => {
    expect(findTradeBarIndex(BAR_TIMES, DAY, FIRST_BAR + DAY + 1)).toBe(1);
  });

  it('puts a trade at the bar start on the bar before', () => {
    expect(findTradeBarIndex(BAR_TIMES, DAY, FIRST_BAR + 2 * DAY)).toBe(1);
  });

  it('finds no bar for a trade before the first bar, after the last bar, or in a gap', () => {
    expect(findTradeBarIndex(BAR_TIMES, DAY, FIRST_BAR)).toBe(-1);
    expect(findTradeBarIndex(BAR_TIMES, DAY, FIRST_BAR + 5 * DAY + 1)).toBe(-1);
    expect(findTradeBarIndex([FIRST_BAR, FIRST_BAR + 3 * DAY], DAY, FIRST_BAR + 2 * DAY)).toBe(-1);
  });
});

describe('groupTradeMarks', () => {
  it('gives one mark for each bar and side', () => {
    const trades = [
      makeTrade(FIRST_BAR + DAY, 'BUY'),
      makeTrade(FIRST_BAR + DAY - 60, 'BUY'),
      makeTrade(FIRST_BAR + DAY, 'SELL'),
      makeTrade(FIRST_BAR + 3 * DAY, 'SELL'),
    ];

    expect(groupTradeMarks(trades, BAR_TIMES, DAY)).toEqual([
      { barIndex: 0, side: 'BUY', tradeIndexes: [0, 1] },
      { barIndex: 0, side: 'SELL', tradeIndexes: [2] },
      { barIndex: 2, side: 'SELL', tradeIndexes: [3] },
    ]);
  });

  it('gives no mark for a trade outside the bars', () => {
    expect(groupTradeMarks([makeTrade(FIRST_BAR - DAY, 'BUY')], BAR_TIMES, DAY)).toEqual([]);
  });
});

describe('mergeTouchingMarks', () => {
  const marks: TradeMark[] = [
    { barIndex: 0, side: 'BUY', tradeIndexes: [0] },
    { barIndex: 1, side: 'BUY', tradeIndexes: [1] },
    { barIndex: 1, side: 'SELL', tradeIndexes: [2] },
    { barIndex: 2, side: 'BUY', tradeIndexes: [3] },
    { barIndex: 4, side: 'BUY', tradeIndexes: [4] },
  ];

  it('keeps all marks when the bar spacing is 16px or more', () => {
    expect(mergeTouchingMarks(marks, 16)).toEqual(marks);
  });

  it('merges the touching marks of one side into one mark at the first bar', () => {
    // 6px: the marks of bars 0, 1, and 2 are less than 16px from bar 0. Bar 4 is 24px from bar 0.
    expect(mergeTouchingMarks(marks, 6)).toEqual([
      { barIndex: 0, side: 'BUY', tradeIndexes: [0, 1, 3] },
      { barIndex: 1, side: 'SELL', tradeIndexes: [2] },
      { barIndex: 4, side: 'BUY', tradeIndexes: [4] },
    ]);
  });
});

describe('layoutTradeMarks', () => {
  const bars = [{ low: 90, high: 110 }];
  const toY = (price: number): number => 200 - price;

  it('puts the B mark 4px below the low and the S mark 4px above the high, with the pointer to the bar', () => {
    const boxes = layoutTradeMarks(
      [
        { barIndex: 0, side: 'BUY', tradeIndexes: [0] },
        { barIndex: 0, side: 'SELL', tradeIndexes: [1] },
      ],
      bars,
      () => 50,
      toY,
    );

    expect(boxes.map(({ x, pointerY, squareTop }) => ({ x, pointerY, squareTop }))).toEqual([
      { x: 50, pointerY: 114, squareTop: 118 },
      { x: 50, pointerY: 86, squareTop: 66 },
    ]);
  });

  it('leaves out a mark without a coordinate', () => {
    expect(
      layoutTradeMarks([{ barIndex: 0, side: 'BUY', tradeIndexes: [0] }], bars, () => null, toY),
    ).toEqual([]);
  });

  it('finds the mark under the pointer', () => {
    const boxes = layoutTradeMarks(
      [{ barIndex: 0, side: 'BUY', tradeIndexes: [0] }],
      bars,
      () => 50,
      toY,
    );

    expect(findMarkAt(boxes, 45, 125)?.mark.tradeIndexes).toEqual([0]);
    expect(findMarkAt(boxes, 30, 125)).toBeUndefined();
  });
});

describe('formatTradeLine', () => {
  it('gives the side, quantity, and price', () => {
    expect(formatTradeLine(makeTrade(0, 'BUY'))).toEqual({ text: 'Buy 50 @ 182.35', profit: null });
  });

  it('gives the signed net profit of the round trip that the trade ends', () => {
    expect(formatTradeLine({ ...makeTrade(0, 'SELL', '387.5'), price: '190.1' })).toEqual({
      text: 'Sell 50 @ 190.10',
      profit: { text: '+387.50', kind: 'success' },
    });
    expect(formatTradeLine(makeTrade(0, 'SELL', '-1234.5')).profit).toEqual({
      text: '−1,234.50',
      kind: 'error',
    });
  });
});

describe('readCenteredRange', () => {
  it('keeps the width of the visible range and puts the bar in the center', () => {
    expect(readCenteredRange({ from: 0, to: 40 }, 30)).toEqual({ from: 10, to: 50 });
  });

  it('gives a narrower range for a bar near the first bar, with at least 10 bars on each side', () => {
    expect(readCenteredRange({ from: 0, to: 44 }, 15)).toEqual({ from: 0, to: 30 });
    expect(readCenteredRange({ from: 0, to: 44 }, 3)).toEqual({ from: -7, to: 13 });
  });
});

describe('listChartTrades', () => {
  it('gives each fill row its chart trade and a split adjustment row none', () => {
    const fill = {
      symbol: 'FTBAR',
      exchange: 'ARCA',
      time_utc: '2025-11-04T00:00:01Z',
      kind: 'fill' as const,
      side: 'SELL' as const,
      quantity_shares: '10',
      price_usd: '101.5',
      commission_usd: '0',
      amount_usd: '1015',
      split_ratio: null,
      round_trip_net_profit_usd: '15',
    };
    const split = {
      ...fill,
      kind: 'split_adjustment' as const,
      price_usd: null,
      round_trip_net_profit_usd: null,
    };

    expect(listChartTrades([split, fill])).toEqual({
      trades: [
        {
          time: FIRST_BAR + DAY + 1,
          side: 'SELL',
          quantity: '10',
          price: '101.5',
          roundTripNetProfit: '15',
        },
      ],
      tradeIndexByRow: [null, 0],
    });
  });
});
