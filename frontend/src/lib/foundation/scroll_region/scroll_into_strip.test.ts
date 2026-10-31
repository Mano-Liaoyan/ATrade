// Computes the scroll position of a sideways strip that shows one item fully, for example the selected tab.
import { describe, expect, it } from 'vite-plus/test';
import { computeScrollLeftToShow } from './index';

describe('computeScrollLeftToShow', () => {
  it('keeps the scroll position when the item is fully visible', () => {
    expect(computeScrollLeftToShow({ scrollLeftPixels: 40, viewportWidthPixels: 200, itemLeftPixels: 60, itemWidthPixels: 80 })).toBe(40);
  });

  it('scrolls back so that the start of an item before the visible part shows', () => {
    expect(computeScrollLeftToShow({ scrollLeftPixels: 100, viewportWidthPixels: 200, itemLeftPixels: 30, itemWidthPixels: 80 })).toBe(30);
  });

  it('scrolls on so that the end of an item after the visible part shows', () => {
    expect(computeScrollLeftToShow({ scrollLeftPixels: 0, viewportWidthPixels: 200, itemLeftPixels: 250, itemWidthPixels: 80 })).toBe(130);
  });

  it('shows the start of an item that is wider than the strip', () => {
    expect(computeScrollLeftToShow({ scrollLeftPixels: 0, viewportWidthPixels: 100, itemLeftPixels: 250, itemWidthPixels: 300 })).toBe(250);
  });

  it('rounds a fractional position so that the item shows fully', () => {
    expect(computeScrollLeftToShow({ scrollLeftPixels: 0, viewportWidthPixels: 200, itemLeftPixels: 250.4, itemWidthPixels: 80.2 })).toBe(131);
    expect(computeScrollLeftToShow({ scrollLeftPixels: 100, viewportWidthPixels: 200, itemLeftPixels: 30.6, itemWidthPixels: 80 })).toBe(30);
  });
});
