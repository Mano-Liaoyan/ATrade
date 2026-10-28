// The parts that the equity and drawdown chart (EquityDrawdownChart), its legend, and the compared key metrics
// (ComparedKeyMetrics) share: the time of a chart point and the line style of each curve. The second curve is a dashed
// line in another color, so the user can tell the curves apart without color.
import { LineStyle, type UTCTimestamp } from 'lightweight-charts';

const MILLISECONDS_PER_SECOND = 1000;

export interface CurveStyle {
  colorVariable: string;
  lineStyle: LineStyle;
}

const FIRST_CURVE_STYLE: CurveStyle = { colorVariable: '--cds-text-primary', lineStyle: LineStyle.Solid };
const CURVE_STYLES: readonly CurveStyle[] = [
  FIRST_CURVE_STYLE,
  { colorVariable: '--cds-interactive', lineStyle: LineStyle.Dashed },
];

/** Chart times are UNIX timestamps (UTC), not date strings (docs/architecture.md section 13). */
export function convertToTimestamp(timeUtc: string): UTCTimestamp {
  return (Date.parse(timeUtc) / MILLISECONDS_PER_SECOND) as UTCTimestamp;
}

export function readCurveStyle(curveIndex: number): CurveStyle {
  return CURVE_STYLES[curveIndex % CURVE_STYLES.length] ?? FIRST_CURVE_STYLE;
}
