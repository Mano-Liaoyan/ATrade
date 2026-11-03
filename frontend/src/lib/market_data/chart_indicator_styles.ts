// The look of indicator lines on a bar chart (docs/architecture/indicator.md section 23.9.3): the Carbon data
// visualization categorical palette (14 colors, checked against @carbon/colors) and the number format of each
// indicator in the legend and on its price scale.
import {
  blue50,
  blue80,
  cyan20,
  cyan40,
  cyan50,
  cyan90,
  green30,
  green60,
  magenta40,
  magenta50,
  magenta60,
  magenta70,
  orange60,
  orange70,
  purple30,
  purple50,
  purple60,
  purple70,
  red10,
  red50,
  red90,
  teal40,
  teal50,
  teal60,
  teal70,
  yellow40,
  yellow50,
} from '@carbon/colors';
import type { PriceFormatCustom } from 'lightweight-charts';
import { CHART_PRICE_FORMAT } from '#lib/foundation/chart_frame';
import { formatPrice } from '#lib/foundation/value_format';

interface PaletteColor {
  name: string;
  hex: string;
}

// The light themes (g10) and the dark theme (g100) have their own palette. A line keeps its color index (1 to 14), so
// a theme change gives it the color of the same index in the other palette.
const LIGHT_PALETTE: readonly PaletteColor[] = [
  { name: 'Purple 70', hex: purple70 },
  { name: 'Cyan 50', hex: cyan50 },
  { name: 'Teal 70', hex: teal70 },
  { name: 'Magenta 70', hex: magenta70 },
  { name: 'Red 50', hex: red50 },
  { name: 'Red 90', hex: red90 },
  { name: 'Green 60', hex: green60 },
  { name: 'Blue 80', hex: blue80 },
  { name: 'Magenta 50', hex: magenta50 },
  { name: 'Yellow 50', hex: yellow50 },
  { name: 'Teal 50', hex: teal50 },
  { name: 'Cyan 90', hex: cyan90 },
  { name: 'Orange 70', hex: orange70 },
  { name: 'Purple 50', hex: purple50 },
];
const DARK_PALETTE: readonly PaletteColor[] = [
  { name: 'Purple 60', hex: purple60 },
  { name: 'Cyan 40', hex: cyan40 },
  { name: 'Teal 60', hex: teal60 },
  { name: 'Magenta 40', hex: magenta40 },
  { name: 'Red 50', hex: red50 },
  { name: 'Red 10', hex: red10 },
  { name: 'Green 30', hex: green30 },
  { name: 'Blue 50', hex: blue50 },
  { name: 'Magenta 60', hex: magenta60 },
  { name: 'Yellow 40', hex: yellow40 },
  { name: 'Teal 40', hex: teal40 },
  { name: 'Cyan 20', hex: cyan20 },
  { name: 'Orange 60', hex: orange60 },
  { name: 'Purple 30', hex: purple30 },
];

export const CHART_PALETTE_SIZE = LIGHT_PALETTE.length;

function readPaletteEntry(color: number, dark: boolean): PaletteColor {
  const palette = dark ? DARK_PALETTE : LIGHT_PALETTE;
  const index = (((Math.round(color) - 1) % CHART_PALETTE_SIZE) + CHART_PALETTE_SIZE) % CHART_PALETTE_SIZE;
  return palette[index] ?? LIGHT_PALETTE[0] ?? { name: '', hex: '' };
}

/** The hex color of palette index `color` (1 to 14) in the light or the dark palette. */
export function readPaletteColor(color: number, dark: boolean): string {
  return readPaletteEntry(color, dark).hex;
}

/** The name of palette index `color`, for example "Purple 70". The settings use it as the accessible name. */
export function readPaletteColorName(color: number, dark: boolean): string {
  return readPaletteEntry(color, dark).name;
}

/** The legend text of a bar without a value. */
export const NO_VALUE_TEXT = 'No value';

type ValueFormat = 'price' | 'decimal' | 'percent' | 'short_amount';

const VALUE_FORMATS: Record<string, ValueFormat> = {
  rsi: 'decimal',
  momentum_12_1: 'percent',
  distance_to_52_week_high: 'percent',
  realized_volatility: 'percent',
  average_trading_value: 'short_amount',
};

// A percent indicator gives a fraction: 0.968 is "96.80 %".
const PERCENT_FACTOR = 100;
const DECIMAL_FORMAT = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
  useGrouping: false,
});
const SHORT_AMOUNT_UNITS: readonly { size: number; suffix: string }[] = [
  { size: 1e12, suffix: 'T' },
  { size: 1e9, suffix: 'B' },
  { size: 1e6, suffix: 'M' },
  { size: 1e3, suffix: 'K' },
];

function formatShortAmount(amount: number): string {
  const unit = SHORT_AMOUNT_UNITS.find((shortUnit) => Math.abs(amount) >= shortUnit.size);
  return unit === undefined ? formatPrice(amount) : `${formatPrice(amount / unit.size)} ${unit.suffix}`;
}

function formatNumber(format: ValueFormat, value: number): string {
  switch (format) {
    case 'decimal':
      return DECIMAL_FORMAT.format(value);
    case 'percent':
      return `${formatPrice(value * PERCENT_FACTOR)} %`;
    case 'short_amount':
      return formatShortAmount(value);
    case 'price':
      return formatPrice(value);
  }
}

/** The value of an indicator line as the legend and the price scale show it, or "No value". */
export function formatIndicatorValue(indicator: string, value: number | null): string {
  return value === null ? NO_VALUE_TEXT : formatNumber(VALUE_FORMATS[indicator] ?? 'price', value);
}

/** The price scale format of an indicator line. Price indicators use the price format of the candlesticks. */
export function readIndicatorPriceFormat(indicator: string): PriceFormatCustom {
  const format = VALUE_FORMATS[indicator] ?? 'price';
  if (format === 'price') {
    return CHART_PRICE_FORMAT;
  }
  return { type: 'custom', minMove: 0.0001, formatter: (value: number) => formatNumber(format, value) };
}
