// The scroll position of a sideways strip that shows one item fully, for example the selected tab of a tab strip.
// Only the strip scrolls: Element.scrollIntoView can also scroll the panels and the page around the strip.

export interface StripItemPosition {
  /** The current scroll position of the strip. */
  scrollLeftPixels: number;
  /** The visible width of the strip. */
  viewportWidthPixels: number;
  /** The start of the item, from the start of the strip content. */
  itemLeftPixels: number;
  itemWidthPixels: number;
}

/**
 * Returns the smallest change of the scroll position that shows the item. An item wider than the strip shows its start.
 * The result is in whole pixels, rounded so that the item shows fully: browsers can round a fractional scroll position.
 */
export function computeScrollLeftToShow(position: StripItemPosition): number {
  const { scrollLeftPixels, viewportWidthPixels, itemLeftPixels, itemWidthPixels } = position;
  if (itemLeftPixels < scrollLeftPixels || itemWidthPixels > viewportWidthPixels) {
    return Math.floor(itemLeftPixels);
  }
  const itemRightPixels = itemLeftPixels + itemWidthPixels;
  if (itemRightPixels > scrollLeftPixels + viewportWidthPixels) {
    return Math.ceil(itemRightPixels - viewportWidthPixels);
  }
  return scrollLeftPixels;
}
