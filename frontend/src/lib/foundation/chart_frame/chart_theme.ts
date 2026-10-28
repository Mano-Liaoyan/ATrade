// The Carbon tokens of the current theme (g10 or g100) for a lightweight-charts chart. A chart reads them when it draws
// and again after each change of the color scheme (watchColorScheme), without a new chart (docs/architecture.md 13).
import type { ChartOptions, DeepPartial, PriceFormatCustom } from 'lightweight-charts';
import { formatPrice, formatSignedPercent } from '#lib/foundation/value_format';

/** The price scale of a price or an equity series: "11,000.00", like the tables. */
export const CHART_PRICE_FORMAT = {
  type: 'custom',
  minMove: 0.01,
  formatter: (price: number) => formatPrice(price),
} satisfies PriceFormatCustom;

/** The price scale of a percent series: "-37.71 %", "0.00 %", the one sign rule of the max drawdown tile. */
export const CHART_PERCENT_FORMAT = {
  type: 'custom',
  minMove: 0.01,
  formatter: (percent: number) => formatSignedPercent(percent),
} satisfies PriceFormatCustom;

function readStyle(container: Element | undefined): CSSStyleDeclaration {
  return getComputedStyle(container ?? document.documentElement);
}

/** The value of a Carbon color token, for example "--cds-support-success", at the canvas container. */
export function readChartColor(container: Element | undefined, variableName: string): string {
  return readStyle(container).getPropertyValue(variableName).trim();
}

/** The background, text, grid, and scale border colors and the font (IBM Plex Sans from the Carbon reset). */
export function readChartThemeOptions(container: Element | undefined): DeepPartial<ChartOptions> {
  const gridColor = readChartColor(container, '--cds-border-subtle-01');
  return {
    layout: {
      background: { color: readChartColor(container, '--cds-layer-01') },
      textColor: readChartColor(container, '--cds-text-secondary'),
      fontFamily: readStyle(container).fontFamily,
    },
    grid: { vertLines: { color: gridColor }, horzLines: { color: gridColor } },
    rightPriceScale: { borderColor: gridColor },
    timeScale: { borderColor: gridColor },
  };
}
