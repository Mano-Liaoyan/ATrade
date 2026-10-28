<!-- A workbench panel: a 32px header line and the panel body that fills the rest of the height. The header line has
     either Carbon tabs (`tabs`) or other content (`header`, for example a price line), and at its right end the
     Minimize and Maximize buttons. A double-click on an empty part of the header line toggles Maximize. The
     Maximize button is the keyboard way to do the same. PanelSplit gives the size and the toggles (`PanelState`).
     The panel is a region named by `label`. When it shows only its header line, the body is hidden. -->
<script module lang="ts">
  import type { PanelSize } from './panel_split';

  /** The state that PanelSplit gives to each of its panels. Spread it on the Panel. */
  export interface PanelState {
    size: PanelSize;
    headerOnly: boolean;
    onToggleMinimized: () => void;
    onToggleMaximized: () => void;
    onRestore: () => void;
  }

  export interface PanelTabs {
    label: string;
    items: readonly { value: string; label: string }[];
    value: string;
    onValueChange: (value: string) => void;
  }
</script>

<script lang="ts">
  import Maximize16 from '@carbon/icons/es/maximize/16.js';
  import Minimize16 from '@carbon/icons/es/minimize/16.js';
  import Subtract16 from '@carbon/icons/es/subtract/16.js';
  import type { Snippet } from 'svelte';
  import { IconButton, Tabs } from '#lib/foundation/carbon';
  import { isEmptyHeaderPart } from './header_target';
  import PanelHeader from './PanelHeader.svelte';

  interface Props extends PanelState {
    label: string;
    tabs?: PanelTabs;
    header?: Snippet;
    children: Snippet;
  }

  const { label, size, headerOnly, onToggleMinimized, onToggleMaximized, onRestore, tabs, header, children }: Props =
    $props();

  // A double-click on an empty part of the header line. Svelte has no event for a part of a child component, so
  // the panel listens and checks that the target is in its header line.
  function toggleMaximizedOnHeader(panel: HTMLElement) {
    const toggle = (event: MouseEvent): void => {
      const headerLine = event.target instanceof Element ? event.target.closest('.atrade-panel-header') : null;
      if (headerLine !== null && panel.contains(headerLine) && isEmptyHeaderPart(event.target)) {
        onToggleMaximized();
      }
    };
    panel.addEventListener('dblclick', toggle);
    return () => {
      panel.removeEventListener('dblclick', toggle);
    };
  }

  // A tab of a panel that shows only its header line opens the panel again.
  function selectTab(value: string): void {
    tabs?.onValueChange(value);
    if (headerOnly) {
      onRestore();
    }
  }
</script>

{#snippet panelButtons()}
  <div class="atrade-panel-header__end">
    <IconButton
      label={size === 'minimized' ? 'Restore panel' : 'Minimize panel'}
      icon={size === 'minimized' ? Minimize16 : Subtract16}
      onclick={onToggleMinimized}
    />
    <IconButton
      label={size === 'maximized' ? 'Restore panel' : 'Maximize panel'}
      icon={size === 'maximized' ? Minimize16 : Maximize16}
      align="bottom-end"
      onclick={onToggleMaximized}
    />
  </div>
{/snippet}

<section class={['panel', headerOnly && 'panel--header-only']} aria-label={label} {@attach toggleMaximizedOnHeader}>
  {#if tabs !== undefined}
    <Tabs
      label={tabs.label}
      items={tabs.items}
      value={tabs.value}
      onValueChange={selectTab}
      size="sm"
      lineClass="atrade-panel-header"
      lineEnd={panelButtons}
      panelClass="panel-body"
      panel={children}
    />
  {:else}
    <PanelHeader end={panelButtons}>
      {@render header?.()}
    </PanelHeader>
    <div class="panel-body">
      {@render children()}
    </div>
  {/if}
</section>

<style>
  .panel {
    display: grid;
    grid-template-rows: auto minmax(0, 1fr);
    block-size: 100%;
    min-block-size: 0;
    min-inline-size: 0;
    overflow: hidden;
  }

  /* Bits UI Tabs.Root is one element around the tab line and the tab panel. */
  .panel > :global([data-tabs-root]) {
    display: grid;
    grid-template-rows: auto minmax(0, 1fr);
    min-block-size: 0;
    grid-row: 1 / -1;
  }

  .panel :global(.panel-body) {
    position: relative;
    display: flex;
    flex-direction: column;
    min-block-size: 0;
    padding: 0;
    overflow: hidden;
  }

  .panel--header-only :global(.panel-body) {
    display: none;
  }
</style>
