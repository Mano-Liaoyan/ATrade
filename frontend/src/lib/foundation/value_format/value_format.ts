// Shows API values in tables and text: bar periods like "1 min", and amounts with thousands separators.

// A bar period of the API is "<step>-<unit>", the NautilusTrader bar specification, for example "15-MINUTE".
const BAR_PERIOD_PATTERN = /^(\d+)-([A-Z]+)$/;
const SHORT_UNIT_NAMES: Record<string, string> = { SECOND: 'sec', MINUTE: 'min' };
const UNIT_NAMES: Record<string, string> = { HOUR: 'hour', DAY: 'day', WEEK: 'week', MONTH: 'month' };
const AMOUNT_FORMAT = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** "1-MINUTE" gives "1 min", "2-HOUR" gives "2 hours", "1-DAY" gives "1 day". An unknown value stays as it is. */
export function formatBarPeriod(barPeriod: string): string {
  const match = BAR_PERIOD_PATTERN.exec(barPeriod);
  if (match === null) {
    return barPeriod;
  }
  const [, step = '', unit = ''] = match;
  const shortName = SHORT_UNIT_NAMES[unit];
  if (shortName !== undefined) {
    return `${step} ${shortName}`;
  }
  const name = UNIT_NAMES[unit];
  if (name === undefined) {
    return barPeriod;
  }
  return step === '1' ? `${step} ${name}` : `${step} ${name}s`;
}

const SIGNED_FORMAT = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
  signDisplay: 'exceptZero',
});
/** The text of a missing value in a table or on a price line. */
export const MISSING_VALUE = '–';

/** Up, down, or flat: ChangeText shows each with its own icon and color. */
export type ChangeDirection = 'up' | 'down' | 'flat';

/** 1.256 gives "+1.26", -1234.5 gives "-1,234.50", 0 gives "0.00". All pages show a change with this sign rule. */
export function formatSignedNumber(value: number | null): string {
  return value === null ? MISSING_VALUE : SIGNED_FORMAT.format(value);
}

/** 0.974 gives "+0.97 %", 0 gives "0.00 %". All pages show a percent change (and the max drawdown) with this rule. */
export function formatSignedPercent(percent: number | null): string {
  return percent === null ? MISSING_VALUE : `${SIGNED_FORMAT.format(percent)} %`;
}

/** 1234.5 gives "1,234.50". */
export function formatPrice(price: number | null): string {
  return price === null ? MISSING_VALUE : AMOUNT_FORMAT.format(price);
}

export function findChangeDirection(change: number | null): ChangeDirection {
  if (change === null || change === 0) {
    return 'flat';
  }
  return change > 0 ? 'up' : 'down';
}

/** "98765.4" gives "98,765.40". The column or the text names the currency. */
export function formatAmount(amount: string): string {
  return AMOUNT_FORMAT.format(Number(amount));
}
