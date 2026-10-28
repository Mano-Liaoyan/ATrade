// The Carbon tokens of the current theme (g10 or g100) for a lightweight-charts chart. A chart reads them when it draws
// and again after each change of the color scheme (watchColorScheme), without a new chart (docs/architecture.md 13).
import type { ChartOptions, DeepPartial } from 'lightweight-charts';

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
