// The size and the position of the app-owned scroll thumb, and the scroll distance of a thumb drag.
import { describe, expect, it } from 'vitest';
import { computeScrollThumb, convertThumbMoveToScrollDistance } from './scroll_thumb';

describe('computeScrollThumb', () => {
  it('hides the thumb when the content fits', () => {
    expect(computeScrollThumb({ clientSize: 300, scrollSize: 300, scrollPosition: 0 })).toEqual({
      isVisible: false,
      sizePercent: 100,
      offsetPercent: 0,
    });
  });

  it('sizes the thumb by the visible part and places it at the scroll position', () => {
    expect(computeScrollThumb({ clientSize: 250, scrollSize: 1000, scrollPosition: 0 })).toEqual({
      isVisible: true,
      sizePercent: 25,
      offsetPercent: 0,
    });
    expect(computeScrollThumb({ clientSize: 250, scrollSize: 1000, scrollPosition: 750 })).toEqual({
      isVisible: true,
      sizePercent: 25,
      offsetPercent: 75,
    });
  });

  it('keeps a very long content thumb large enough to grab', () => {
    const thumb = computeScrollThumb({ clientSize: 100, scrollSize: 100_000, scrollPosition: 0 });

    expect(thumb.sizePercent).toBe(10);
  });
});

describe('convertThumbMoveToScrollDistance', () => {
  it('moves the content by the same part of its scroll range as the thumb moves on its track', () => {
    const scrollDistance = convertThumbMoveToScrollDistance({
      thumbMovePixels: 75,
      trackSizePixels: 400,
      thumbSizePercent: 25,
      clientSize: 250,
      scrollSize: 1000,
    });

    expect(scrollDistance).toBe(187.5);
  });
});
