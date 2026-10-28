<!-- A side column of a workbench, at the start (left) or at the end (right). It has a 32px header line with its name and
     the Collapse button, and its body fills the rest of the height. A collapsed column is a 32px wide rail with the
     Open button, like TradingView. The body stays in the page while the column is collapsed, so a form keeps its
     values. The browser keeps the choice under `storageKey`. The button names use the lower-case `label`, for
     example "Collapse watchlist" and "Open watchlist". -->
<script lang="ts">
  import RightPanelClose16 from '@carbon/icons/es/right-panel--close/16.js';
  import RightPanelOpen16 from '@carbon/icons/es/right-panel--open/16.js';
  import SidePanelClose16 from '@carbon/icons/es/side-panel--close/16.js';
  import SidePanelOpen16 from '@carbon/icons/es/side-panel--open/16.js';
  import { untrack, type Snippet } from 'svelte';
  import { IconButton } from '#lib/foundation/carbon';
  import PanelHeader from './PanelHeader.svelte';
  import { readSideColumnLayout, readStoredLayout, writeStoredLayout } from './stored_layout';

  interface Props {
    /** The name of the column: its heading and its accessible name. */
    label: string;
    side: 'start' | 'end';
    storageKey: string;
    /** The width of the open column. */
    width?: string;
    children: Snippet;
  }

  const { label, side, storageKey, width = '17.5rem', children }: Props = $props();

  // The layout of the first render: a change of storageKey does not apply to a column that shows.
  let isCollapsed = $state(untrack(() => readSideColumnLayout(readStoredLayout(storageKey)).isCollapsed));
  $effect(() => {
    writeStoredLayout(storageKey, { isCollapsed });
  });

  const name = $derived(label.toLowerCase());
  const isStart = $derived(side === 'start');
</script>

<aside
  class={['side-column', `side-column--${side}`, isCollapsed && 'side-column--rail']}
  aria-label={label}
  style:inline-size={isCollapsed ? 'var(--cds-spacing-07)' : width}
>
  {#if isCollapsed}
    <IconButton
      label={`Open ${name}`}
      icon={isStart ? SidePanelOpen16 : RightPanelOpen16}
      align={isStart ? 'right' : 'left'}
      onclick={() => {
        isCollapsed = false;
      }}
    />
  {:else}
    <PanelHeader>
      <h2>{label}</h2>
      {#snippet end()}
        <IconButton
          label={`Collapse ${name}`}
          icon={isStart ? SidePanelClose16 : RightPanelClose16}
          align="bottom-end"
          onclick={() => {
            isCollapsed = true;
          }}
        />
      {/snippet}
    </PanelHeader>
  {/if}
  <div class="side-column-body" hidden={isCollapsed}>
    {@render children()}
  </div>
</aside>

<style>
  .side-column {
    display: grid;
    flex: none;
    grid-template-rows: auto minmax(0, 1fr);
    box-sizing: border-box;
    min-block-size: 0;
    overflow: hidden;
  }

  .side-column--start {
    border-inline-end: 1px solid var(--cds-border-subtle-01);
  }

  .side-column--end {
    border-inline-start: 1px solid var(--cds-border-subtle-01);
  }

  /* The rail: the Open button at the top of a 32px wide column. */
  .side-column--rail {
    grid-template-rows: auto;
    align-content: start;
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
