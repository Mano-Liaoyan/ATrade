<!-- The splitter above a panel (WAI-ARIA window splitter pattern). Its value is the height of that panel (`controls`
     is its element id) in pixels. A pointer drag moves it. With the focus, Arrow Up and Arrow Down move it 16px, Home
     gives the panel its minimum height, and End its maximum height. -->
<script lang="ts">
  import { findSplitterDragValue, findSplitterKeyValue, type SplitterDrag } from './splitter';

  interface Props {
    label: string;
    /** The id of the panel element that the splitter resizes. */
    controls: string;
    value: number;
    min: number;
    max: number;
    onValueChange: (value: number) => void;
  }

  const { label, controls, value, min, max, onValueChange }: Props = $props();

  const KEY_STEP_PIXELS = 16;

  let drag: SplitterDrag | null = null;

  function startDrag(event: PointerEvent): void {
    if (!(event.currentTarget instanceof HTMLElement)) {
      return;
    }
    event.currentTarget.setPointerCapture(event.pointerId);
    drag = { startPointerPixels: event.clientY, startValue: value };
  }

  function moveDrag(event: PointerEvent): void {
    if (drag !== null) {
      onValueChange(findSplitterDragValue(drag, event.clientY, { min, max }));
    }
  }

  function endDrag(): void {
    drag = null;
  }

  function moveWithKey(event: KeyboardEvent): void {
    const newValue = findSplitterKeyValue(event.key, { value, min, max, step: KEY_STEP_PIXELS });
    if (newValue !== null) {
      event.preventDefault();
      onValueChange(newValue);
    }
  }
</script>

<!-- A focusable separator is a widget in WAI-ARIA (window splitter pattern); Svelte treats every separator as static. -->
<!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
<div
  class="splitter"
  role="separator"
  tabindex="0"
  aria-label={label}
  aria-controls={controls}
  aria-orientation="horizontal"
  aria-valuemin={min}
  aria-valuemax={max}
  aria-valuenow={value}
  onpointerdown={startDrag}
  onpointermove={moveDrag}
  onpointerup={endDrag}
  onpointercancel={endDrag}
  onkeydown={moveWithKey}
></div>

<style>
  .splitter {
    block-size: var(--cds-spacing-02);
    background: var(--cds-border-subtle-01);
    cursor: row-resize;
    touch-action: none;
  }

  .splitter:hover {
    background: var(--cds-border-strong-01);
  }

  .splitter:focus-visible {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }
</style>
