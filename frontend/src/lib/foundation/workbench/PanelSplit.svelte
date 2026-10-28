<!-- Stacked workbench panels with a splitter between 2 open panels (panel_split.ts). `panels` lists the panels from top
     to bottom; the first one fills the rest of the height. The `panel` snippet gets the id and the PanelState of each
     panel; spread the state on a Panel. While a panel is maximized, no splitter shows.
     Escape restores a maximized panel of the split that has the focus. Inside nested splits, the innermost maximized
     split restores first. With the focus outside all splits, Escape restores this split. The browser keeps the layout
     under `storageKey`. `openPanel(id)` (through `bind:this`) opens a panel that shows only its header line or its
     status bar, for example when the page has a message for that panel. -->
<script lang="ts">
  import { untrack, type Snippet } from 'svelte';
  import type { PanelState } from './Panel.svelte';
  import {
    findPanelPixelRange,
    findPanelSize,
    isPanelHeaderOnly,
    listPanelRows,
    openPanel as openPanelInLayout,
    readPanelSplitLayout,
    restorePanelSplit,
    togglePanelSize,
    type PanelSpec,
    type PanelSplitLayout,
  } from './panel_split';
  import Splitter from './Splitter.svelte';
  import { readStoredLayout, writeStoredLayout } from './stored_layout';

  interface Props {
    storageKey: string;
    panels: readonly PanelSpec[];
    panel: Snippet<[string, PanelState]>;
  }

  const { storageKey, panels, panel }: Props = $props();

  const uid = $props.id();
  // The layout of the first render: a change of storageKey does not apply to a panel split that shows.
  let layout: PanelSplitLayout = $state(untrack(() => readPanelSplitLayout(readStoredLayout(storageKey), panels)));
  $effect(() => {
    writeStoredLayout(storageKey, layout);
  });

  let totalPixels = $state(0);
  const rows = $derived(listPanelRows(layout, panels, shownPixels()));

  // The heights inside the limits of the current area height.
  function shownPixels(): Record<string, number> {
    if (totalPixels === 0) {
      return layout.pixels;
    }
    const pixels: Record<string, number> = {};
    for (const [id, value] of Object.entries(layout.pixels)) {
      const range = findPanelPixelRange(layout, panels, id, totalPixels);
      pixels[id] = Math.min(Math.max(value, range.min), range.max);
    }
    return pixels;
  }

  function createPanelState(id: string): PanelState {
    return {
      size: findPanelSize(layout, id),
      headerOnly: isPanelHeaderOnly(layout, id),
      onToggleMinimized: () => {
        layout = togglePanelSize(layout, panels, id, 'minimized');
      },
      onToggleMaximized: () => {
        layout = togglePanelSize(layout, panels, id, 'maximized');
      },
      onRestore: () => {
        layout = { ...layout, maximized: null, minimized: layout.minimized.filter((minimizedId) => minimizedId !== id) };
      },
    };
  }

  /** Opens a panel that shows only its header line or its status bar. */
  export function openPanel(id: string): void {
    layout = openPanelInLayout(layout, id);
  }

  function findPanel(id: string): PanelSpec | undefined {
    return panels.find((candidate) => candidate.id === id);
  }

  // A dialog, a menu, or a list box uses Escape first.
  function isEscapeForSplit(event: KeyboardEvent): boolean {
    const isInPopup =
      event.target instanceof Element && event.target.closest('[role="dialog"], [role="menu"], [role="listbox"]') !== null;
    return event.key === 'Escape' && !event.defaultPrevented && !isInPopup && layout.maximized !== null;
  }

  // The focus is in this split: the innermost maximized split restores, and its parent splits do not.
  function restoreOnEscapeInSplit(event: KeyboardEvent): void {
    if (isEscapeForSplit(event)) {
      event.preventDefault();
      layout = restorePanelSplit(layout);
    }
  }

  // The focus is outside all splits, for example on the page after a reload.
  function restoreOnEscapeOutside(event: KeyboardEvent): void {
    const isInSplit = event.target instanceof Element && event.target.closest('.panel-split') !== null;
    if (!isInSplit && isEscapeForSplit(event)) {
      layout = restorePanelSplit(layout);
    }
  }
</script>

<svelte:window onkeydown={restoreOnEscapeOutside} />

<!-- The keydown handler only restores a maximized panel with Escape. The panels have their own controls. -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="panel-split"
  style:grid-template-rows={rows.map((row) => (row.kind === 'panel' ? row.track : 'auto')).join(' ')}
  bind:clientHeight={totalPixels}
  onkeydown={restoreOnEscapeInSplit}
>
  {#each rows as row (`${row.kind}-${row.id}`)}
    {#if row.kind === 'panel'}
      <div class="panel-slot" id={`${uid}-${row.id}`}>{@render panel(row.id, createPanelState(row.id))}</div>
    {:else}
      {@const range = findPanelPixelRange(layout, panels, row.id, totalPixels)}
      <Splitter
        label={findPanel(row.id)?.splitterLabel ?? row.id}
        controls={`${uid}-${row.id}`}
        value={shownPixels()[row.id] ?? range.min}
        min={range.min}
        max={range.max}
        onValueChange={(value: number) => {
          layout = { ...layout, pixels: { ...layout.pixels, [row.id]: value } };
        }}
      />
    {/if}
  {/each}
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
