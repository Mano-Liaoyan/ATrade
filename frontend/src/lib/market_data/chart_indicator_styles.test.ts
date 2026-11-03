import { describe, expect, it } from 'vite-plus/test';
import {
  CHART_PALETTE_SIZE,
  formatIndicatorValue,
  isHistogramLine,
  readPaletteColor,
  readPaletteColorName,
} from './chart_indicator_styles';

describe('chart indicator styles', () => {
  it('formats prices, RSI, percents, and short amounts as the legend shows them', () => {
    expect(formatIndicatorValue('sma', 11000)).toBe('11,000.00');
    expect(formatIndicatorValue('bollinger_bands', 191.2)).toBe('191.20');
    expect(formatIndicatorValue('macd', -0.456)).toBe('-0.46');
    expect(formatIndicatorValue('rsi', 75.856)).toBe('75.86');
    expect(formatIndicatorValue('momentum_12_1', -0.032)).toBe('-3.20 %');
    expect(formatIndicatorValue('distance_to_52_week_high', 0.968)).toBe('96.80 %');
    expect(formatIndicatorValue('realized_volatility', 0.2512)).toBe('25.12 %');
    expect(formatIndicatorValue('average_trading_value', 12_345_000_000)).toBe('12.35 B');
    expect(formatIndicatorValue('average_trading_value', 820_100_000)).toBe('820.10 M');
    expect(formatIndicatorValue('average_trading_value', 45_600)).toBe('45.60 K');
    expect(formatIndicatorValue('average_trading_value', 512)).toBe('512.00');
    expect(formatIndicatorValue('average_trading_value', 3_200_000_000_000)).toBe('3.20 T');
  });

  it('draws the MACD histogram and the average trading value as histograms, all other outputs as lines', () => {
    expect(isHistogramLine('macd', 'histogram')).toBe(true);
    expect(isHistogramLine('average_trading_value', 'value')).toBe(true);
    expect(isHistogramLine('macd', 'value')).toBe(false);
    expect(isHistogramLine('macd', 'signal')).toBe(false);
    expect(isHistogramLine('rsi', 'value')).toBe(false);
  });

  it('shows "No value" for a bar without a value', () => {
    expect(formatIndicatorValue('sma', null)).toBe('No value');
    expect(formatIndicatorValue('rsi', null)).toBe('No value');
  });

  it('has the 14 Carbon categorical colors for the light and the dark themes', () => {
    expect(CHART_PALETTE_SIZE).toBe(14);
    expect(readPaletteColor(1, false)).toBe('#6929c4');
    expect(readPaletteColorName(1, false)).toBe('Purple 70');
    expect(readPaletteColor(1, true)).toBe('#8a3ffc');
    expect(readPaletteColorName(1, true)).toBe('Purple 60');
    expect(readPaletteColorName(6, false)).toBe('Red 90');
    expect(readPaletteColorName(6, true)).toBe('Red 10');
    expect(readPaletteColorName(14, false)).toBe('Purple 50');
    expect(readPaletteColorName(14, true)).toBe('Purple 30');
  });
});
