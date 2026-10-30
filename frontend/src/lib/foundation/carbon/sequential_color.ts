// The Carbon sequential colors of a heatmap: the monochromatic Blue 10 to Blue 100 palette of Carbon data
// visualization, from @carbon/colors. The Carbon themes have no tokens for them. From Blue 60, the text is white.
import { blue10, blue20, blue30, blue40, blue50, blue60, blue70, blue80, blue90, blue100, gray100, white } from '@carbon/colors';

const SEQUENTIAL_BLUES = [blue10, blue20, blue30, blue40, blue50, blue60, blue70, blue80, blue90, blue100];
const FIRST_WHITE_TEXT_STEP = 6;

/** The background and text color of step 1 (lowest) to 10 (highest). */
export function readSequentialColor(step: number): { background: string; text: string } {
  const index = Math.min(Math.max(Math.round(step), 1), SEQUENTIAL_BLUES.length) - 1;
  return {
    background: SEQUENTIAL_BLUES[index] ?? blue10,
    text: index + 1 >= FIRST_WHITE_TEXT_STEP ? white : gray100,
  };
}
