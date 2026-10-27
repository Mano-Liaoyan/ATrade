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

/** "98765.4" gives "98,765.40". The column or the text names the currency. */
export function formatAmount(amount: string): string {
  return AMOUNT_FORMAT.format(Number(amount));
}
