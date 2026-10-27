<!-- A region that scrolls inside itself, with app-owned scroll tracks and thumbs that every desktop browser shows. -->
<script lang="ts">
  import type { Snippet } from 'svelte';
  import { computeScrollThumb, convertThumbMoveToScrollDistance, type ScrollThumb } from './scroll_thumb';

  type Axis = 'vertical' | 'horizontal';

  const {
    children,
    label,
    maxBlockSize,
  }: { children: Snippet; label: string; maxBlockSize: string } = $props();

  const componentId = $props.id();
  const viewportId = `${componentId}-viewport`;
  const hiddenThumb: ScrollThumb = { isVisible: false, sizePercent: 100, offsetPercent: 0 };
  let viewport: HTMLDivElement | undefined = $state();
  let content: HTMLDivElement | undefined = $state();
  let verticalThumb: ScrollThumb = $state(hiddenThumb);
  let horizontalThumb: ScrollThumb = $state(hiddenThumb);
  let drag: { axis: Axis; startPointerPixels: number; startScrollPixels: number } | null = null;

  function updateThumbs(): void {
    if (viewport === undefined) {
      return;
    }
    verticalThumb = computeScrollThumb({
      clientSize: viewport.clientHeight,
      scrollSize: viewport.scrollHeight,
      scrollPosition: viewport.scrollTop,
    });
    horizontalThumb = computeScrollThumb({
      clientSize: viewport.clientWidth,
      scrollSize: viewport.scrollWidth,
      scrollPosition: viewport.scrollLeft,
    });
  }

  $effect(() => {
    if (viewport === undefined || content === undefined) {
      return;
    }
    const resizeObserver = new ResizeObserver(updateThumbs);
    resizeObserver.observe(viewport);
    resizeObserver.observe(content);
    updateThumbs();
    return () => {
      resizeObserver.disconnect();
    };
  });

  function readPointerPixels(event: PointerEvent, axis: Axis): number {
    return axis === 'vertical' ? event.clientY : event.clientX;
  }

  function readScrollPixels(axis: Axis): number {
    if (viewport === undefined) {
      return 0;
    }
    return axis === 'vertical' ? viewport.scrollTop : viewport.scrollLeft;
  }

  function startThumbDrag(event: PointerEvent, axis: Axis): void {
    event.stopPropagation();
    event.preventDefault();
    (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
    drag = { axis, startPointerPixels: readPointerPixels(event, axis), startScrollPixels: readScrollPixels(axis) };
  }

  function moveThumb(event: PointerEvent): void {
    if (drag === null || viewport === undefined) {
      return;
    }
    const track = (event.currentTarget as HTMLElement).parentElement;
    if (track === null) {
      return;
    }
    const isVertical = drag.axis === 'vertical';
    const scrollDistance = convertThumbMoveToScrollDistance({
      thumbMovePixels: readPointerPixels(event, drag.axis) - drag.startPointerPixels,
      trackSizePixels: isVertical ? track.clientHeight : track.clientWidth,
      thumbSizePercent: isVertical ? verticalThumb.sizePercent : horizontalThumb.sizePercent,
      clientSize: isVertical ? viewport.clientHeight : viewport.clientWidth,
      scrollSize: isVertical ? viewport.scrollHeight : viewport.scrollWidth,
    });
    const scrollPixels = drag.startScrollPixels + scrollDistance;
    if (isVertical) {
      viewport.scrollTop = scrollPixels;
    } else {
      viewport.scrollLeft = scrollPixels;
    }
  }

  function stopThumbDrag(): void {
    drag = null;
  }

  // A press on the track outside the thumb scrolls by one visible page toward the press.
  function scrollOnePage(event: PointerEvent, axis: Axis): void {
    if (viewport === undefined) {
      return;
    }
    const thumb = (event.currentTarget as HTMLElement).firstElementChild;
    if (thumb === null) {
      return;
    }
    const thumbBox = thumb.getBoundingClientRect();
    const pointerPixels = readPointerPixels(event, axis);
    const thumbStartPixels = axis === 'vertical' ? thumbBox.top : thumbBox.left;
    const direction = pointerPixels < thumbStartPixels ? -1 : 1;
    if (axis === 'vertical') {
      viewport.scrollBy({ top: direction * viewport.clientHeight });
    } else {
      viewport.scrollBy({ left: direction * viewport.clientWidth });
    }
  }
</script>

<div class="scroll-area">
  <!-- readability-exception: a scroll region needs keyboard focus for arrow-key scrolling, and Safari does not give it focus by itself. -->
  <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
  <div
    id={viewportId}
    class="scroll-viewport"
    style:max-block-size={maxBlockSize}
    bind:this={viewport}
    onscroll={updateThumbs}
    role="region"
    aria-label={label}
    tabindex="0"
  >
    <div class="scroll-content" bind:this={content}>
      {@render children()}
    </div>
  </div>
  {#if verticalThumb.isVisible}
    <div
      class="scroll-track scroll-track-vertical"
      data-scroll-track="vertical"
      role="scrollbar"
      aria-label="{label} vertical scroll bar"
      aria-orientation="vertical"
      aria-valuenow={Math.round(verticalThumb.offsetPercent)}
      aria-controls={viewportId}
      tabindex="-1"
      onpointerdown={(event) => {
        scrollOnePage(event, 'vertical');
      }}
    >
      <div
        class="scroll-thumb"
        data-scroll-thumb="vertical"
        role="presentation"
        style:block-size="{verticalThumb.sizePercent}%"
        style:inset-block-start="{verticalThumb.offsetPercent}%"
        onpointerdown={(event) => {
          startThumbDrag(event, 'vertical');
        }}
        onpointermove={moveThumb}
        onpointerup={stopThumbDrag}
        onpointercancel={stopThumbDrag}
      ></div>
    </div>
  {/if}
  {#if horizontalThumb.isVisible}
    <div
      class="scroll-track scroll-track-horizontal"
      data-scroll-track="horizontal"
      role="scrollbar"
      aria-label="{label} horizontal scroll bar"
      aria-orientation="horizontal"
      aria-valuenow={Math.round(horizontalThumb.offsetPercent)}
      aria-controls={viewportId}
      tabindex="-1"
      onpointerdown={(event) => {
        scrollOnePage(event, 'horizontal');
      }}
    >
      <div
        class="scroll-thumb"
        data-scroll-thumb="horizontal"
        role="presentation"
        style:inline-size="{horizontalThumb.sizePercent}%"
        style:inset-inline-start="{horizontalThumb.offsetPercent}%"
        onpointerdown={(event) => {
          startThumbDrag(event, 'horizontal');
        }}
        onpointermove={moveThumb}
        onpointerup={stopThumbDrag}
        onpointercancel={stopThumbDrag}
      ></div>
    </div>
  {/if}
</div>

<style>
  .scroll-area {
    --scroll-track-size: 0.625rem;
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    grid-template-rows: minmax(0, 1fr) auto;
    min-inline-size: 0;
  }

  .scroll-viewport {
    grid-column: 1;
    grid-row: 1;
    overflow: auto;
    /* The app draws its own tracks, so the native scrollbars are hidden in every browser. */
    scrollbar-width: none;
  }

  .scroll-viewport::-webkit-scrollbar {
    display: none;
  }

  .scroll-track {
    position: relative;
    border-radius: calc(var(--scroll-track-size) / 2);
    background: var(--color-scroll-track, #d0d7de66);
    touch-action: none;
  }

  .scroll-track-vertical {
    grid-column: 2;
    grid-row: 1;
    inline-size: var(--scroll-track-size);
    margin-inline-start: 0.25rem;
  }

  .scroll-track-horizontal {
    grid-column: 1;
    grid-row: 2;
    block-size: var(--scroll-track-size);
    margin-block-start: 0.25rem;
  }

  .scroll-thumb {
    position: absolute;
    border-radius: calc(var(--scroll-track-size) / 2);
    background: var(--color-scroll-thumb, #59636e);
    cursor: grab;
  }

  .scroll-track-vertical .scroll-thumb {
    inset-inline: 0;
  }

  .scroll-track-horizontal .scroll-thumb {
    inset-block: 0;
  }
</style>
