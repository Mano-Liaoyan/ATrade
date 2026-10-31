<!-- The app-owned horizontal scroll track and thumb of an element that scrolls sideways, for example a tab strip.
     Safari can hide native scrollbars, so the element hides them in all browsers and this track shows the position
     (docs/architecture.md section 13.1). The parent places the track (for example along the bottom edge of the strip).
     The track shows only while the content is wider than the element. A drag on the thumb scrolls, a click on the track
     scrolls one page, and the arrow keys, Home, and End scroll when the track has the focus. A vertical mouse wheel on
     the element scrolls it sideways. -->
<script lang="ts">
  import { computeScrollThumb, computeScrollTopForThumbTop, type ScrollThumb } from './scroll_thumb';

  interface Props {
    /** The accessible name of the scrolled element; the track is "<label> scroll bar". */
    label: string;
    /** The element that scrolls sideways. */
    viewport: HTMLElement | undefined;
    /** The element in the viewport that has the full width of the content. */
    content: HTMLElement | undefined;
    /** The ID of the viewport, for aria-controls. */
    viewportId: string;
    class?: string;
  }

  const { label, viewport, content, viewportId, class: className }: Props = $props();

  const ARROW_KEY_STEP_PIXELS = 40;
  const PERCENT = 100;

  let scrollThumb: ScrollThumb = $state({ isOverflowing: false, thumbHeightPixels: 0, thumbTopPixels: 0 });
  let scrolledPercent = $state(0);
  let trackWidthPixels = $state(0);
  let thumbDragStart: { pointerXPixels: number; thumbLeftPixels: number } | undefined;

  function measureScroll(): void {
    if (viewport === undefined) {
      return;
    }
    // The thumb functions measure one axis: here the width and the left edge.
    scrollThumb = computeScrollThumb({
      scrollTopPixels: viewport.scrollLeft,
      contentHeightPixels: viewport.scrollWidth,
      viewportHeightPixels: viewport.clientWidth,
    });
    trackWidthPixels = viewport.clientWidth;
    const scrollRangePixels = viewport.scrollWidth - viewport.clientWidth;
    scrolledPercent = scrollRangePixels > 0 ? Math.round((viewport.scrollLeft / scrollRangePixels) * PERCENT) : 0;
  }

  // A vertical wheel step scrolls the strip sideways, because the strip has no vertical scroll.
  function scrollWithWheel(event: WheelEvent): void {
    if (viewport === undefined || viewport.scrollWidth <= viewport.clientWidth || event.deltaY === 0) {
      return;
    }
    if (Math.abs(event.deltaX) > Math.abs(event.deltaY)) {
      return;
    }
    event.preventDefault();
    viewport.scrollBy({ left: event.deltaY });
  }

  $effect(() => {
    const element = viewport;
    if (element === undefined) {
      return;
    }
    const resizeObserver = new ResizeObserver(measureScroll);
    resizeObserver.observe(element);
    if (content !== undefined) {
      resizeObserver.observe(content);
    }
    element.addEventListener('scroll', measureScroll, { passive: true });
    element.addEventListener('wheel', scrollWithWheel, { passive: false });
    return () => {
      resizeObserver.disconnect();
      element.removeEventListener('scroll', measureScroll);
      element.removeEventListener('wheel', scrollWithWheel);
    };
  });

  function startTrackPointer(event: PointerEvent): void {
    if (viewport === undefined || !(event.currentTarget instanceof HTMLElement)) {
      return;
    }
    const isOnThumb = event.target instanceof HTMLElement && event.target.classList.contains('scroll-thumb');
    if (!isOnThumb) {
      const trackLeftPixels = event.currentTarget.getBoundingClientRect().left;
      const isBeforeThumb = event.clientX - trackLeftPixels < scrollThumb.thumbTopPixels;
      viewport.scrollBy({ left: (isBeforeThumb ? -1 : 1) * viewport.clientWidth });
      return;
    }
    event.currentTarget.setPointerCapture(event.pointerId);
    thumbDragStart = { pointerXPixels: event.clientX, thumbLeftPixels: scrollThumb.thumbTopPixels };
  }

  function moveThumb(event: PointerEvent): void {
    if (viewport === undefined || thumbDragStart === undefined) {
      return;
    }
    viewport.scrollLeft = computeScrollTopForThumbTop({
      thumbTopPixels: thumbDragStart.thumbLeftPixels + event.clientX - thumbDragStart.pointerXPixels,
      contentHeightPixels: viewport.scrollWidth,
      viewportHeightPixels: viewport.clientWidth,
    });
  }

  function endThumbDrag(): void {
    thumbDragStart = undefined;
  }

  function scrollWithKey(event: KeyboardEvent): void {
    if (viewport === undefined) {
      return;
    }
    const scrollStepsByKey: Record<string, number> = {
      ArrowRight: ARROW_KEY_STEP_PIXELS,
      ArrowLeft: -ARROW_KEY_STEP_PIXELS,
      PageDown: viewport.clientWidth,
      PageUp: -viewport.clientWidth,
      End: viewport.scrollWidth,
      Home: -viewport.scrollWidth,
    };
    const scrollStepPixels = scrollStepsByKey[event.key];
    if (scrollStepPixels === undefined) {
      return;
    }
    event.preventDefault();
    viewport.scrollBy({ left: scrollStepPixels });
  }
</script>

{#if scrollThumb.isOverflowing}
  <div
    class={['scroll-track', className]}
    role="scrollbar"
    tabindex="0"
    aria-label={`${label} scroll bar`}
    aria-controls={viewportId}
    aria-orientation="horizontal"
    aria-valuemin={0}
    aria-valuemax={PERCENT}
    aria-valuenow={scrolledPercent}
    style:inline-size={`${String(trackWidthPixels)}px`}
    onpointerdown={startTrackPointer}
    onpointermove={moveThumb}
    onpointerup={endThumbDrag}
    onpointercancel={endThumbDrag}
    onkeydown={scrollWithKey}
  >
    <div
      class="scroll-thumb"
      style:width={`${String(scrollThumb.thumbHeightPixels)}px`}
      style:transform={`translateX(${String(scrollThumb.thumbTopPixels)}px)`}
    ></div>
  </div>
{/if}

<style>
  /* Carbon tokens only. */
  .scroll-track {
    position: relative;
    block-size: var(--cds-spacing-02);
    background: var(--cds-layer-accent-01);
    touch-action: none;
  }

  .scroll-track:focus-visible {
    outline: 2px solid var(--cds-focus);
    outline-offset: 1px;
  }

  .scroll-thumb {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    background: var(--cds-icon-secondary);
    cursor: grab;
  }

  .scroll-track:hover .scroll-thumb {
    background: var(--cds-icon-primary);
  }
</style>
