// Reads the /ws/market-data messages and decides which live bars the chart can draw.
import { describe, expect, it } from 'vite-plus/test';
import { canDrawLiveBar, describeLiveBar, formatLiveBarsPath, readLiveBarMessage } from './index';

const TENCENT = { symbol: '700', exchange: 'SEHK', currency: 'HKD' };
const BAR = { time: 1767322800, open: 123, high: 125, low: 122, close: 123.25, volume: 20 };

describe('formatLiveBarsPath', () => {
  it('names the instrument and the bar period in the socket path', () => {
    const path = formatLiveBarsPath({ instrument: { ...TENCENT, symbol: 'BRK B' }, barPeriod: '1-HOUR' });

    expect(path).toBe('/ws/market-data?symbol=BRK+B&exchange=SEHK&currency=HKD&bar_period=1-HOUR');
  });
});

describe('readLiveBarMessage', () => {
  it('reads a bar message', () => {
    expect(readLiveBarMessage({ type: 'bar', bar: BAR })).toEqual({ type: 'bar', bar: BAR });
  });

  it('reads an error message', () => {
    const message = { type: 'error', detail: 'IB Gateway is not reachable at ib-gateway:4004. Live bars need IB Gateway.' };

    expect(readLiveBarMessage(message)).toEqual(message);
  });

  it('leaves out other messages', () => {
    expect(readLiveBarMessage({ type: 'account' })).toBeNull();
    expect(readLiveBarMessage('bar')).toBeNull();
    expect(readLiveBarMessage(null)).toBeNull();
  });
});

describe('canDrawLiveBar', () => {
  const earlierBar = { ...BAR, time: BAR.time - 3600 };

  it('draws a live bar that replaces the last bar or comes after it', () => {
    expect(canDrawLiveBar([earlierBar], BAR)).toBe(true);
    expect(canDrawLiveBar([earlierBar, BAR], { ...BAR, close: 124 })).toBe(true);
    expect(canDrawLiveBar([], BAR)).toBe(true);
  });

  it('does not draw a live bar older than the last bar', () => {
    expect(canDrawLiveBar([BAR], earlierBar)).toBe(false);
  });
});

describe('describeLiveBar', () => {
  it('names the bar start in UTC and the close with 2 decimals', () => {
    expect(describeLiveBar(BAR)).toBe('Live bar 2026-01-02 03:00 UTC: close 123.25');
    expect(describeLiveBar({ ...BAR, close: 123 })).toBe('Live bar 2026-01-02 03:00 UTC: close 123.00');
  });
});
