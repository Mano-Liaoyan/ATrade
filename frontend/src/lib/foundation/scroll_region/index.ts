// Public entry of foundation/scroll_region: a region with its own visible scroll track and thumb in every browser.
export { default as ScrollRegion } from './ScrollRegion.svelte';
export { computeScrollThumb, computeScrollTopForThumbTop, type ScrollThumb } from './scroll_thumb';
export { default as HorizontalScrollTrack } from './HorizontalScrollTrack.svelte';
export { computeScrollLeftToShow, type StripItemPosition } from './scroll_into_strip';
