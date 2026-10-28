<!-- Two stacked workbench panels with the splitter between them. The `first` and `second` snippets get the PanelState
     of their panel; spread it on a Panel. One panel at a time can be minimized or maximized (panel_split.ts). While a
     panel is minimized or maximized, the splitter is hidden. Escape restores a maximized panel. The browser keeps the
     layout (the mode and the height of the second panel) under `storageKey`. -->
<script lang="ts">
  import { untrack, type Snippet } from 'svelte';
  import type { PanelState } from './Panel.svelte';
  import {
    clampSecondPanelPixels,
    findPanelSize,
    formatPanelRows,
    isPanelHeaderOnly,
    readPanelSplitLayout,
    restorePanelSplit,
    togglePanelSize,
    type PanelPosition,
  } from './panel_split';
  import Splitter from './Splitter.svelte';
  import { readStoredLayout, writeStoredLayout } from './stored_layout';

  interface Props {
    storageKey: string;
    /** The accessible name of the splitter, for example "Resize the chart and the paper account". */
    splitterLabel: string;
    defaultSecondPixels?: number;
    minFirstPixels?: number;
    minSecondPixels?: number;
    first: Snippet<[PanelState]>;
    second: Snippet<[PanelState]>;
  }

  // Default sizes in pixels: the second panel shows about 6 table rows, and each panel keeps its header line and
  // some content.
  const DEFAULT_SECOND_PIXELS = 240;
  const DEFAULT_MIN_FIRST_PIXELS = 160;
  const DEFAULT_MIN_SECOND_PIXELS = 96;

  const {
    storageKey,
    splitterLabel,
    defaultSecondPixels = DEFAULT_SECOND_PIXELS,
    minFirstPixels = DEFAULT_MIN_FIRST_PIXELS,
    minSecondPixels = DEFAULT_MIN_SECOND_PIXELS,
    first,
    second,
  }: Props = $props();

  // The layout of the first render: a change of storageKey does not apply to a panel split that shows.
  const layout = $state(
    untrack(() =>
      readPanelSplitLayout(readStoredLayout(storageKey), { mode: 'split', secondPixels: defaultSecondPixels }),
    ),
  );
  $effect(() => {
    writeStoredLayout(storageKey, { mode: layout.mode, secondPixels: layout.secondPixels });
  });

  let totalPixels = $state(0);
  const limits = $derived({ totalPixels, minFirstPixels, minSecondPixels });
  const maxSecondPixels = $derived(Math.max(minSecondPixels, totalPixels - minFirstPixels));
  const shownSecondPixels = $derived(
    totalPixels > 0 ? clampSecondPanelPixels(layout.secondPixels, limits) : layout.secondPixels,
  );

  function createPanelState(position: PanelPosition): PanelState {
    return {
      size: findPanelSize(layout.mode, position),
      headerOnly: isPanelHeaderOnly(layout.mode, position),
      onToggleMinimized: () => {
        layout.mode = togglePanelSize(layout.mode, position, 'minimized');
      },
      onToggleMaximized: () => {
        layout.mode = togglePanelSize(layout.mode, position, 'maximized');
      },
      onRestore: () => {
        layout.mode = 'split';
      },
    };
  }

  // A dialog, a menu, or a list box uses Escape first.
  function restoreOnEscape(event: KeyboardEvent): void {
    const isInPopup =
      event.target instanceof Element && event.target.closest('[role="dialog"], [role="menu"], [role="listbox"]') !== null;
    if (event.key === 'Escape' && !event.defaultPrevented && !isInPopup) {
      layout.mode = restorePanelSplit(layout.mode);
    }
  }
</script>

<svelte:window onkeydown={restoreOnEscape} />

<div
  class="panel-split"
  style:grid-template-rows={formatPanelRows(layout.mode, shownSecondPixels)}
  bind:clientHeight={totalPixels}
>
  <div class="panel-slot">{@render first(createPanelState('first'))}</div>
  {#if layout.mode === 'split'}
    <Splitter
      label={splitterLabel}
      value={shownSecondPixels}
      min={minSecondPixels}
      max={maxSecondPixels}
      onValueChange={(value: number) => {
        layout.secondPixels = value;
      }}
    />
  {/if}
  <div class="panel-slot">{@render second(createPanelState('second'))}</div>
</div>

<style>
  .panel-split {
    display: grid;
    flex: 1 1 0;
    min-block-size: 0;
    min-inline-size: 0;
    block-size: 100%;
  }

  .panel-slot {
    min-block-size: 0;
    min-inline-size: 0;
  }
</style>
