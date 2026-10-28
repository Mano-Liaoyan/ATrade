<!-- PROTOTYPE (#99), throwaway: the 32px tab line of a workbench panel. The tabs on the left, the Minimize and Maximize
     icon buttons on the right. A double-click on an empty part of the line toggles maximize, like VS Code. -->
<script lang="ts">
  import ChevronDown16 from '@carbon/icons/es/chevron--down/16.js';
  import Maximize16 from '@carbon/icons/es/maximize/16.js';
  import Minimize16 from '@carbon/icons/es/minimize/16.js';
  import Subtract16 from '@carbon/icons/es/subtract/16.js';
  import type { Snippet } from 'svelte';
  import type { PanelSize } from './workbench_layout';
  import WorkbenchIconButton from './WorkbenchIconButton.svelte';

  interface Props {
    size: PanelSize;
    // The output panel minimizes to the status bar: its minimize button is a chevron and has no restore state.
    minimizesToStatusBar?: boolean;
    onToggleMinimized: () => void;
    onToggleMaximized: () => void;
    children: Snippet;
  }

  const { size, minimizesToStatusBar = false, onToggleMinimized, onToggleMaximized, children }: Props = $props();

  const isMinimized = $derived(size === 'minimized');
  const isMaximized = $derived(size === 'maximized');

  function toggleMaximizedOnEmptyPart(event: MouseEvent): void {
    const isOnControl = event.target instanceof Element && event.target.closest('button, [role="tab"]') !== null;
    if (!isOnControl) {
      onToggleMaximized();
    }
  }
</script>

<!-- The Maximize button is the keyboard way to do the same as the double-click. -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="tab-line cds--layout--size-sm" ondblclick={toggleMaximizedOnEmptyPart}>
  <div class="tab-line-tabs">
    {@render children()}
  </div>
  <div class="tab-line-controls">
    {#if minimizesToStatusBar}
      <WorkbenchIconButton label="Minimize panel" icon={ChevronDown16} onclick={onToggleMinimized} />
    {:else}
      <WorkbenchIconButton
        label={isMinimized ? 'Restore panel' : 'Minimize panel'}
        icon={isMinimized ? Minimize16 : Subtract16}
        onclick={onToggleMinimized}
      />
    {/if}
    <WorkbenchIconButton
      label={isMaximized ? 'Restore panel' : 'Maximize panel'}
      icon={isMaximized ? Minimize16 : Maximize16}
      align="bottom-end"
      onclick={onToggleMaximized}
    />
  </div>
</div>

<style>
  .tab-line {
    display: flex;
    flex: none;
    align-items: stretch;
    block-size: var(--cds-spacing-07);
    border-block-end: 1px solid var(--cds-border-subtle-01);
  }

  .tab-line-tabs {
    flex: 1;
    min-inline-size: 0;
    overflow-x: auto;
    overflow-y: hidden;
    scrollbar-width: thin;
    scrollbar-color: var(--cds-icon-secondary) transparent;
  }

  .tab-line-tabs :global(.cds--tabs) {
    block-size: 100%;
    min-block-size: 0;
  }

  .tab-line-controls {
    display: flex;
    flex: none;
  }
</style>
