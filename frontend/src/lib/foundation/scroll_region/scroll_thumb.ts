// Size and position of the app scroll thumb. The track has the height of the viewport.

// A short thumb is hard to grab with a mouse.
const MINIMUM_THUMB_HEIGHT_PIXELS = 24;

export interface ScrollMeasurement {
  scrollTopPixels: number;
  contentHeightPixels: number;
  viewportHeightPixels: number;
}

export interface ScrollThumb {
  isOverflowing: boolean;
  thumbHeightPixels: number;
  thumbTopPixels: number;
}

export function computeScrollThumb(measurement: ScrollMeasurement): ScrollThumb {
  const { scrollTopPixels, contentHeightPixels, viewportHeightPixels } = measurement;
  if (contentHeightPixels <= viewportHeightPixels) {
    return { isOverflowing: false, thumbHeightPixels: viewportHeightPixels, thumbTopPixels: 0 };
  }
  const visibleShare = viewportHeightPixels / contentHeightPixels;
  const thumbHeightPixels = Math.max(MINIMUM_THUMB_HEIGHT_PIXELS, viewportHeightPixels * visibleShare);
  const scrollRangePixels = contentHeightPixels - viewportHeightPixels;
  const scrolledShare = Math.min(1, Math.max(0, scrollTopPixels / scrollRangePixels));
  const thumbTopPixels = (viewportHeightPixels - thumbHeightPixels) * scrolledShare;
  return { isOverflowing: true, thumbHeightPixels, thumbTopPixels };
}

export function computeScrollTopForThumbTop(position: {
  thumbTopPixels: number;
  contentHeightPixels: number;
  viewportHeightPixels: number;
}): number {
  const { thumbTopPixels, contentHeightPixels, viewportHeightPixels } = position;
  const { thumbHeightPixels } = computeScrollThumb({ scrollTopPixels: 0, contentHeightPixels, viewportHeightPixels });
  const thumbRangePixels = viewportHeightPixels - thumbHeightPixels;
  if (thumbRangePixels <= 0) {
    return 0;
  }
  const thumbShare = Math.min(1, Math.max(0, thumbTopPixels / thumbRangePixels));
  return thumbShare * (contentHeightPixels - viewportHeightPixels);
}
