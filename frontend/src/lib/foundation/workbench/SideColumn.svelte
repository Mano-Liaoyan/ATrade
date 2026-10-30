<!-- A side column of a workbench, at the start (left) or at the end (right). It has a 32px header line with its name and
     the Minimize button, and its body fills the rest of the height. A vertical splitter on the inner edge changes the
     width: a drag, Arrow Left and Arrow Right 16px, Home the minimum, End the maximum, and a double-click the default
     width. The width is 16rem to 60% of the workbench, and the center area keeps at least 24rem (side_column.ts). A
     minimized column is a 32px wide rail with the Open button, and it opens with the width from before. The body stays
     in the page while the column is minimized, so a form keeps its values. The browser keeps the width and the
     minimized state under `storageKey`. The button names use the lower-case `label`, for example "Minimize watchlist"
     and "Open watchlist". `actions` adds icon buttons before the Minimize button. `railIcon` is the icon of the Open
     button of the rail. With `maximizable`, the column has a Maximize button: the column gets all the width of the
     workbench except the other side columns and a 32px rail of the center area. A second click or Escape restores
     the width from before. `onMaximizedChange` tells the page, so the center area can show only its rail. -->
<script lang="ts">
  import Maximize16 from '@carbon/icons/es/maximize/16.js';
  import Minimize16 from '@carbon/icons/es/minimize/16.js';
  import RightPanelClose16 from '@carbon/icons/es/right-panel--close/16.js';
  import RightPanelOpen16 from '@carbon/icons/es/right-panel--open/16.js';
  import SidePanelClose16 from '@carbon/icons/es/side-panel--close/16.js';
  import SidePanelOpen16 from '@carbon/icons/es/side-panel--open/16.js';
  import { untrack, type Snippet } from 'svelte';
  import { IconButton, type CarbonIconNode } from '#lib/foundation/carbon';
  import PanelHeader from './PanelHeader.svelte';
  import Splitter from './Splitter.svelte';
  import {
    DEFAULT_REM_PIXELS,
    findSideColumnGrowDirection,
    findSideColumnRange,
    findSideColumnWidth,
    readRemPixels,
    readSideColumnLayout,
  } from './side_column';
  import { readStoredLayout, writeStoredLayout } from './stored_layout';

  interface Props {
    /** The name of the column: its heading and its accessible name. */
    label: string;
    side: 'start' | 'end';
    storageKey: string;
    /** The default width of the open column, in rem or px. */
    width?: string;
    /** Icon buttons of the column (IconButton) in its header line, before the Minimize button. */
    actions?: Snippet;
    /** The icon of the Open button of the rail. Default: the side panel icon. */
    railIcon?: CarbonIconNode;
    /** The name in the button names. Default: the lower-case label. */
    buttonName?: string;
    maximizable?: boolean;
    onMaximizedChange?: (isMaximized: boolean) => void;
    children: Snippet;
  }

  const {
    label,
    side,
    storageKey,
    width = '17.5rem',
    actions,
    railIcon,
    buttonName,
    maximizable = false,
    onMaximizedChange,
    children,
  }: Props = $props();

  const id = $props.id();

  // The layout of the first render: a change of storageKey does not apply to a column that shows.
  const storedLayout = untrack(() => readSideColumnLayout(readStoredLayout(storageKey)));
  let isMinimized = $state(storedLayout.isMinimized);
  /** The width that the user set. Null gives the default width. */
  let widthPixels = $state(storedLayout.widthPixels);
  $effect(() => {
    writeStoredLayout(storageKey, { isMinimized, widthPixels });
  });

  // Maximize is not stored: a reload shows the width from before.
  let isMaximized = $state(false);
  function setMaximized(value: boolean): void {
    if (value !== isMaximized) {
      isMaximized = value;
      onMaximizedChange?.(value);
    }
  }

  function restoreOnEscape(event: KeyboardEvent): void {
    if (isMaximized && event.key === 'Escape' && !event.defaultPrevented) {
      setMaximized(false);
    }
  }

  // The workbench measures: zero until the column is in the page.
  let column: HTMLElement | undefined = $state();
  let workbenchPixels = $state(0);
  let otherColumnsPixels = $state(0);
  let remPixels = $state(DEFAULT_REM_PIXELS);

  $effect(() => {
    const workbench = column?.parentElement;
    if (column === undefined || workbench === null || workbench === undefined) {
      return;
    }
    const self = column;
    const measure = (): void => {
      remPixels = readRemPixels();
      workbenchPixels = workbench.clientWidth;
      const others = [...workbench.children].filter((child) => child !== self && child.matches('.side-column'));
      otherColumnsPixels = others.reduce((sum, other) => sum + other.getBoundingClientRect().width, 0);
    };
    const observer = new ResizeObserver(measure);
    observer.observe(workbench);
    for (const child of workbench.children) {
      if (child.matches('.side-column')) {
        observer.observe(child);
      }
    }
    measure();
    return () => {
      observer.disconnect();
    };
  });

  const range = $derived(findSideColumnRange({ workbenchPixels, otherColumnsPixels, remPixels }));
  const shownPixels = $derived(findSideColumnWidth(widthPixels, width, range, remPixels));
  // Before the first measure, the column shows the stored or the default width without the range.
  const openWidth = $derived.by(() => {
    if (workbenchPixels > 0) {
      return `${String(shownPixels)}px`;
    }
    return widthPixels === null ? width : `${String(widthPixels)}px`;
  });

  const name = $derived(buttonName ?? label.toLowerCase());
  // All the width except the other side columns and the 32px rail of the center area.
  const maximizedWidth = $derived(
    `calc(${String(workbenchPixels - otherColumnsPixels)}px - var(--cds-spacing-07))`,
  );
  const shownWidth = $derived(isMinimized ? 'var(--cds-spacing-07)' : isMaximized ? maximizedWidth : openWidth);
  const isStart = $derived(side === 'start');
</script>

<svelte:window onkeydown={restoreOnEscape} />

<aside
  {id}
  bind:this={column}
  class={['side-column', `side-column--${side}`, isMinimized && 'side-column--rail']}
  aria-label={label}
  style:inline-size={shownWidth}
>
  <div class="side-column-content">
    {#if isMinimized}
      <IconButton
        label={`Open ${name}`}
        icon={railIcon ?? (isStart ? SidePanelOpen16 : RightPanelOpen16)}
        align={isStart ? 'right' : 'left'}
        onclick={() => {
          isMinimized = false;
        }}
      />
    {:else}
      <PanelHeader>
        <h2>{label}</h2>
        {#snippet end()}
          {@render actions?.()}
          {#if maximizable}
            <IconButton
              label={isMaximized ? `Restore ${name}` : `Maximize ${name}`}
              icon={isMaximized ? Minimize16 : Maximize16}
              onclick={() => {
                setMaximized(!isMaximized);
              }}
            />
          {/if}
          <IconButton
            label={`Minimize ${name}`}
            icon={isStart ? SidePanelClose16 : RightPanelClose16}
            align="bottom-end"
            onclick={() => {
              setMaximized(false);
              isMinimized = true;
            }}
          />
        {/snippet}
      </PanelHeader>
    {/if}
    <div class="side-column-body" hidden={isMinimized}>
      {@render children()}
    </div>
  </div>
  {#if !isMinimized && !isMaximized}
    <Splitter
      label={`Resize ${name}`}
      controls={id}
      value={shownPixels}
      min={range.min}
      max={range.max}
      grow={findSideColumnGrowDirection(side)}
      onValueChange={(value: number) => {
        widthPixels = value;
      }}
      ondblclick={() => {
        widthPixels = null;
      }}
    />
  {/if}
</aside>

<style>
  .side-column {
    display: flex;
    flex: none;
    box-sizing: border-box;
    min-block-size: 0;
    overflow: hidden;
  }

  /* The splitter is on the inner edge: after the content of a left column, before the content of a right column. */
  .side-column--end {
    flex-direction: row-reverse;
  }

  .side-column-content {
    display: grid;
    flex: 1 1 0;
    grid-template-rows: auto minmax(0, 1fr);
    min-block-size: 0;
    min-inline-size: 0;
    overflow: hidden;
  }

  /* The rail: the Open button at the top of a 32px wide column, with a border on the inner edge. */
  .side-column--rail .side-column-content {
    grid-template-rows: auto;
    align-content: start;
  }

  .side-column--start.side-column--rail {
    border-inline-end: 1px solid var(--cds-border-subtle-01);
  }

  .side-column--end.side-column--rail {
    border-inline-start: 1px solid var(--cds-border-subtle-01);
  }

  .side-column-body {
    display: flex;
    flex-direction: column;
    min-block-size: 0;
    overflow: hidden;
  }

  .side-column-body[hidden] {
    display: none;
  }
</style>
