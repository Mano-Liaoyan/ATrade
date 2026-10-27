import { describe, expect, it } from 'vitest';
import { CODE_COLORS } from './code_colors';

// WCAG 2.2 relative luminance and contrast ratio (https://www.w3.org/TR/WCAG22/#dfn-contrast-ratio).
function readLuminance(hexColor: string): number {
  const channels = [1, 3, 5].map((start) => Number.parseInt(hexColor.slice(start, start + 2), 16) / 255);
  const [red = 0, green = 0, blue = 0] = channels.map((channel) =>
    channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4,
  );
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

function readContrastRatio(firstColor: string, secondColor: string): number {
  const [lighter, darker] = [readLuminance(firstColor), readLuminance(secondColor)].sort((first, second) => second - first);
  return ((lighter ?? 0) + 0.05) / ((darker ?? 0) + 0.05);
}

// WCAG AA for normal text.
const MIN_TEXT_CONTRAST = 4.5;

describe('CODE_COLORS', () => {
  for (const [scheme, colors] of Object.entries(CODE_COLORS)) {
    for (const [role, color] of Object.entries(colors.text)) {
      it(`${scheme} ${role} text meets WCAG AA contrast on the code background`, () => {
        expect(readContrastRatio(color, colors.background)).toBeGreaterThanOrEqual(MIN_TEXT_CONTRAST);
      });
    }
  }

  it('checks the contrast formula with black on white', () => {
    expect(readContrastRatio('#000000', '#ffffff')).toBeCloseTo(21, 5);
  });
});
