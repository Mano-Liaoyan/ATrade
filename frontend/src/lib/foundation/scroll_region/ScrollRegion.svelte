<!-- A region that scrolls inside itself, with an app-owned track and thumb. Safari can hide native scrollbars, so the
     region hides them in all browsers and draws its own (docs/architecture.md section 13.1).
     With `fill`, the region takes the full height of its parent (a workbench panel) and scrolls in it.
     With `stretchContent`, the content is at least as high as the viewport, so it can put a control at the bottom. -->
<script lang="ts">
  import type { Snippet } from 'svelte';
  import { computeScrollThumb, computeScrollTopForThumbTop, type ScrollThumb } from './scroll_thumb';

  interface Props {
    label: string;
    /** The maximum height of the viewport. Not used with `fill`. */
    maxHeight?: string;
    fill?: boolean;
    /** The content is at least as high as the viewport. */
    stretchContent?: boolean;
    children: Snippet;
  }

  const { label, maxHeight, fill = false, stretchContent = false, children }: Props = $props();

  // One arrow key press scrolls this far, like a mouse wheel step.
  const ARROW_KEY_STEP_PIXELS = 40;
  const PERCENT = 100;

  const viewportId = $props.id();
  let viewport: HTMLDivElement | undefined = $state();
  let content: HTMLDivElement | undefined = $state();
  let scrollThumb: ScrollThumb = $state({ isOverflowing: false, thumbHeightPixels: 0, thumbTopPixels: 0 });
  let scrolledPercent = $state(0);
  let thumbDragStart: { pointerYPixels: number; thumbTopPixels: number } | undefined;

  function measureScroll(): void {
    if (viewport === undefined) {
      return;
    }
    scrollThumb = computeScrollThumb({
      scrollTopPixels: viewport.scrollTop,
      contentHeightPixels: viewport.scrollHeight,
      viewportHeightPixels: viewport.clientHeight,
    });
    const scrollRangePixels = viewport.scrollHeight - viewport.clientHeight;
    scrolledPercent = scrollRangePixels > 0 ? Math.round((viewport.scrollTop / scrollRangePixels) * PERCENT) : 0;
  }

  $effect(() => {
    if (viewport === undefined || content === undefined) {
      return;
    }
    // The content height changes when the list changes. The viewport height changes with the window.
    const resizeObserver = new ResizeObserver(measureScroll);
    resizeObserver.observe(viewport);
    resizeObserver.observe(content);
    return () => {
      resizeObserver.disconnect();
    };
  });

  function startTrackPointer(event: PointerEvent): void {
    if (viewport === undefined || !(event.currentTarget instanceof HTMLElement)) {
      return;
    }
    const isOnThumb = event.target instanceof HTMLElement && event.target.classList.contains('scroll-thumb');
    if (!isOnThumb) {
      const trackTopPixels = event.currentTarget.getBoundingClientRect().top;
      const isAboveThumb = event.clientY - trackTopPixels < scrollThumb.thumbTopPixels;
      const pageDirection = isAboveThumb ? -1 : 1;
      viewport.scrollBy({ top: pageDirection * viewport.clientHeight });
      return;
    }
    event.currentTarget.setPointerCapture(event.pointerId);
    thumbDragStart = { pointerYPixels: event.clientY, thumbTopPixels: scrollThumb.thumbTopPixels };
  }

  function moveThumb(event: PointerEvent): void {
    if (viewport === undefined || thumbDragStart === undefined) {
      return;
    }
    viewport.scrollTop = computeScrollTopForThumbTop({
      thumbTopPixels: thumbDragStart.thumbTopPixels + event.clientY - thumbDragStart.pointerYPixels,
      contentHeightPixels: viewport.scrollHeight,
      viewportHeightPixels: viewport.clientHeight,
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
      ArrowDown: ARROW_KEY_STEP_PIXELS,
      ArrowUp: -ARROW_KEY_STEP_PIXELS,
      PageDown: viewport.clientHeight,
      PageUp: -viewport.clientHeight,
      End: viewport.scrollHeight,
      Home: -viewport.scrollHeight,
    };
    const scrollStepPixels = scrollStepsByKey[event.key];
    if (scrollStepPixels === undefined) {
      return;
    }
    event.preventDefault();
    viewport.scrollBy({ top: scrollStepPixels });
  }
</script>

<div class={['scroll-region', fill && 'scroll-region--fill']}>
  <div
    class="scroll-viewport"
    id={viewportId}
    role="region"
    aria-label={label}
    style:max-height={fill ? undefined : maxHeight}
    bind:this={viewport}
    onscroll={measureScroll}
  >
    <div class={['scroll-content', stretchContent && 'scroll-content--stretch']} bind:this={content}>
      {@render children()}
    </div>
  </div>
  {#if scrollThumb.isOverflowing}
    <div
      class="scroll-track"
      role="scrollbar"
      tabindex="0"
      aria-label={`${label} scroll bar`}
      aria-controls={viewportId}
      aria-orientation="vertical"
      aria-valuemin={0}
      aria-valuemax={PERCENT}
      aria-valuenow={scrolledPercent}
      onpointerdown={startTrackPointer}
      onpointermove={moveThumb}
      onpointerup={endThumbDrag}
      onpointercancel={endThumbDrag}
      onkeydown={scrollWithKey}
    >
      <div
        class="scroll-thumb"
        style:height={`${String(scrollThumb.thumbHeightPixels)}px`}
        style:transform={`translateY(${String(scrollThumb.thumbTopPixels)}px)`}
      ></div>
    </div>
  {/if}
</div>

<style>
  /* Carbon tokens only. */
  .scroll-region {
    display: flex;
    gap: var(--cds-spacing-02);
    min-height: 0;
  }

  .scroll-region--fill {
    block-size: 100%;
  }

  .scroll-viewport {
    flex: 1;
    min-width: 0;
    overflow-y: auto;
    scrollbar-width: none;
  }

  .scroll-content--stretch {
    display: flex;
    flex-direction: column;
    box-sizing: border-box;
    min-block-size: 100%;
  }

  .scroll-viewport::-webkit-scrollbar {
    display: none;
  }

  .scroll-track {
    position: relative;
    flex: none;
    width: var(--cds-spacing-03);
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
    right: 0;
    left: 0;
    background: var(--cds-icon-secondary);
    cursor: grab;
  }

  .scroll-track:hover .scroll-thumb {
    background: var(--cds-icon-primary);
  }
</style>
