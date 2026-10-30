<!-- A splitter (WAI-ARIA window splitter pattern). Its value is the size in pixels of the region that it controls
     (`controls` is its element id): the height of the panel below it, or the width of a side column. `grow` is the
     direction in which the splitter moves to make that region bigger: "up" gives a horizontal splitter (Arrow Up and
     Arrow Down), "left" and "right" give a vertical splitter (Arrow Left and Arrow Right). A pointer drag moves it. With
     the focus, the arrow keys move it 16px, Home gives the region its minimum size, and End its maximum size. -->
<script lang="ts">
  import { findSplitterDragValue, findSplitterKeyValue, type SplitterDrag, type SplitterGrowDirection } from './splitter';

  interface Props {
    label: string;
    /** The id of the element that the splitter resizes. */
    controls: string;
    value: number;
    min: number;
    max: number;
    grow?: SplitterGrowDirection;
    onValueChange: (value: number) => void;
    ondblclick?: () => void;
  }

  const { label, controls, value, min, max, grow = 'up', onValueChange, ondblclick }: Props = $props();

  const KEY_STEP_PIXELS = 16;

  const isVertical = $derived(grow !== 'up');

  let drag: SplitterDrag | null = null;

  function pointerPixels(event: PointerEvent): number {
    return isVertical ? event.clientX : event.clientY;
  }

  function startDrag(event: PointerEvent): void {
    if (!(event.currentTarget instanceof HTMLElement)) {
      return;
    }
    event.currentTarget.setPointerCapture(event.pointerId);
    drag = { startPointerPixels: pointerPixels(event), startValue: value };
  }

  function moveDrag(event: PointerEvent): void {
    if (drag !== null) {
      onValueChange(findSplitterDragValue(drag, pointerPixels(event), { min, max }, grow));
    }
  }

  function endDrag(): void {
    drag = null;
  }

  function moveWithKey(event: KeyboardEvent): void {
    const newValue = findSplitterKeyValue(event.key, { value, min, max, step: KEY_STEP_PIXELS }, grow);
    if (newValue !== null) {
      event.preventDefault();
      onValueChange(newValue);
    }
  }
</script>

<!-- A focusable separator is a widget in WAI-ARIA (window splitter pattern); Svelte treats every separator as static. -->
<!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
<div
  class={['splitter', isVertical && 'splitter--vertical']}
  role="separator"
  tabindex="0"
  aria-label={label}
  aria-controls={controls}
  aria-orientation={isVertical ? 'vertical' : 'horizontal'}
  aria-valuemin={Math.round(min)}
  aria-valuemax={Math.round(max)}
  aria-valuenow={Math.round(value)}
  onpointerdown={startDrag}
  onpointermove={moveDrag}
  onpointerup={endDrag}
  onpointercancel={endDrag}
  onkeydown={moveWithKey}
  {ondblclick}
></div>

<style>
  .splitter {
    flex: none;
    block-size: var(--cds-spacing-02);
    background: var(--cds-border-subtle-01);
    cursor: row-resize;
    touch-action: none;
  }

  .splitter--vertical {
    block-size: auto;
    inline-size: var(--cds-spacing-02);
    cursor: col-resize;
  }

  .splitter:hover {
    background: var(--cds-border-strong-01);
  }

  .splitter:focus-visible {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }
</style>
