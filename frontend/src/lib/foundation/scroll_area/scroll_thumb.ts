// Computes the app-owned scroll thumb along one axis. Safari can hide native scrollbars (docs/architecture.md section 13.1).

export interface ScrollThumb {
  isVisible: boolean;
  sizePercent: number;
  offsetPercent: number;
}

interface ScrollAxis {
  clientSize: number;
  scrollSize: number;
  scrollPosition: number;
}

const FULL_PERCENT = 100;
// A smaller thumb is hard to grab with the mouse.
const MINIMUM_THUMB_SIZE_PERCENT = 10;
// Browsers round sizes, so a content that is 1 pixel larger than its box still fits.
const ROUNDING_TOLERANCE_PIXELS = 1;

export function computeScrollThumb(axis: ScrollAxis): ScrollThumb {
  const scrollRange = axis.scrollSize - axis.clientSize;
  if (scrollRange <= ROUNDING_TOLERANCE_PIXELS) {
    return { isVisible: false, sizePercent: FULL_PERCENT, offsetPercent: 0 };
  }
  const visiblePercent = (axis.clientSize / axis.scrollSize) * FULL_PERCENT;
  const sizePercent = Math.max(visiblePercent, MINIMUM_THUMB_SIZE_PERCENT);
  const scrolledPart = Math.min(Math.max(axis.scrollPosition / scrollRange, 0), 1);
  return { isVisible: true, sizePercent, offsetPercent: scrolledPart * (FULL_PERCENT - sizePercent) };
}

export function convertThumbMoveToScrollDistance(move: {
  thumbMovePixels: number;
  trackSizePixels: number;
  thumbSizePercent: number;
  clientSize: number;
  scrollSize: number;
}): number {
  const thumbRangePixels = move.trackSizePixels * (1 - move.thumbSizePercent / FULL_PERCENT);
  if (thumbRangePixels <= 0) {
    return 0;
  }
  return (move.thumbMovePixels / thumbRangePixels) * (move.scrollSize - move.clientSize);
}
