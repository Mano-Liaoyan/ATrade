// Computes the size and position of the app scroll thumb, and the scroll position for a dragged thumb.
import { describe, expect, it } from 'vitest';
import { computeScrollThumb, computeScrollTopForThumbTop } from './index';

describe('computeScrollThumb', () => {
  it('reports no overflow when the content fits', () => {
    const scrollThumb = computeScrollThumb({ scrollTopPixels: 0, contentHeightPixels: 200, viewportHeightPixels: 200 });

    expect(scrollThumb.isOverflowing).toBe(false);
  });

  it('sizes the thumb by the visible part of the content', () => {
    const scrollThumb = computeScrollThumb({ scrollTopPixels: 0, contentHeightPixels: 800, viewportHeightPixels: 200 });

    expect(scrollThumb).toEqual({ isOverflowing: true, thumbHeightPixels: 50, thumbTopPixels: 0 });
  });

  it('moves the thumb to the end of the track at the end of the content', () => {
    const scrollThumb = computeScrollThumb({ scrollTopPixels: 600, contentHeightPixels: 800, viewportHeightPixels: 200 });

    expect(scrollThumb).toEqual({ isOverflowing: true, thumbHeightPixels: 50, thumbTopPixels: 150 });
  });

  it('keeps a minimum thumb height for very long content', () => {
    const scrollThumb = computeScrollThumb({ scrollTopPixels: 0, contentHeightPixels: 100_000, viewportHeightPixels: 200 });

    expect(scrollThumb.thumbHeightPixels).toBe(24);
  });
});

describe('computeScrollTopForThumbTop', () => {
  it('turns a thumb position into the matching scroll position', () => {
    const scrollTopPixels = computeScrollTopForThumbTop({
      thumbTopPixels: 75,
      contentHeightPixels: 800,
      viewportHeightPixels: 200,
    });

    expect(scrollTopPixels).toBe(300);
  });
});
