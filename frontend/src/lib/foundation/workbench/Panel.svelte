<!-- A workbench panel: a 32px header line and the panel body that fills the rest of the height. The header line has
     either Carbon tabs (`tabs`) or other content (`header`, for example a price line), and at its right end the
     Minimize and Maximize buttons. A double-click on an empty part of the header line toggles Maximize. The
     Maximize button is the keyboard way to do the same. PanelSplit gives the size and the toggles (`PanelState`).
     The panel is a region named by `label`. When it shows only its header line, the body is hidden.
     With `statusBar`, the panel works like the VS Code panel: a 24px status bar is always at the bottom of the panel,
     and a panel that shows only its header line shows only the status bar. The snippet gives the content of the status
     bar (controls with the class `atrade-status-bar__item`); a control in it can call `onRestore` of the PanelState to
     open the panel again. A click on the selected tab minimizes the panel. -->
<script module lang="ts">
  import type { Snippet } from 'svelte';
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
    /** The text of a tab (Tabs `itemLabel`), for example a name with a ChangeText. */
    itemLabel?: Snippet<[{ value: string; label: string }]>;
    /** Tabs that never scroll away, after the strip of `items` (Tabs `fixedItems`). */
    fixedItems?: readonly { value: string; label: string }[];
    /** Closes a tab of `items` (Tabs `onCloseItem`). */
    onCloseItem?: (value: string) => void;
  }
</script>

<script lang="ts">
  import Maximize16 from '@carbon/icons/es/maximize/16.js';
  import Minimize16 from '@carbon/icons/es/minimize/16.js';
  import Subtract16 from '@carbon/icons/es/subtract/16.js';
  import { IconButton, Tabs } from '#lib/foundation/carbon';
  import { isEmptyHeaderPart } from './header_target';
  import PanelHeader from './PanelHeader.svelte';

  interface Props extends PanelState {
    label: string;
    tabs?: PanelTabs;
    header?: Snippet;
    statusBar?: Snippet;
    children: Snippet;
  }

  const {
    label,
    size,
    headerOnly,
    onToggleMinimized,
    onToggleMaximized,
    onRestore,
    tabs,
    header,
    statusBar,
    children,
  }: Props = $props();

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

  const hasStatusBar = $derived(statusBar !== undefined);

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

<section
  class={['panel', headerOnly && 'panel--header-only', hasStatusBar && 'panel--status-bar']}
  aria-label={label}
  {@attach toggleMaximizedOnHeader}
>
  {#if hasStatusBar && headerOnly}
    <!-- Only the status bar below shows. -->
  {:else if tabs !== undefined}
    <Tabs
      label={tabs.label}
      items={tabs.items}
      value={tabs.value}
      onValueChange={selectTab}
      itemLabel={tabs.itemLabel}
      fixedItems={tabs.fixedItems}
      onCloseItem={tabs.onCloseItem}
      onSelectedTabClick={hasStatusBar ? onToggleMinimized : undefined}
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
  {#if statusBar !== undefined}
    <div class="atrade-status-bar">{@render statusBar()}</div>
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

  /* With `statusBar`: the header line, the body, and the 24px status bar at the bottom. */
  .panel--status-bar {
    grid-template-rows: auto minmax(0, 1fr) auto;
  }

  .panel--status-bar > :global([data-tabs-root]) {
    grid-row: 1 / 3;
  }

  .panel--status-bar.panel--header-only {
    grid-template-rows: auto;
  }

  .atrade-status-bar {
    display: flex;
    grid-row: -2 / -1;
    align-items: stretch;
    box-sizing: border-box;
    block-size: var(--cds-spacing-06);
    border-block-start: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-01);
    font-size: var(--cds-helper-text-01-font-size);
    line-height: var(--cds-helper-text-01-line-height);
    letter-spacing: var(--cds-helper-text-01-letter-spacing);
  }

  .atrade-status-bar :global(.atrade-status-bar__item) {
    display: inline-flex;
    align-items: center;
    gap: var(--cds-spacing-04);
    padding: 0 var(--cds-spacing-04);
    border: 0;
    background: transparent;
    color: var(--cds-text-secondary);
    font: inherit;
    cursor: pointer;
  }

  .atrade-status-bar :global(.atrade-status-bar__item:hover) {
    background: var(--cds-layer-hover-01);
    color: var(--cds-text-primary);
  }

  .atrade-status-bar :global(.atrade-status-bar__item:focus-visible) {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }
</style>
