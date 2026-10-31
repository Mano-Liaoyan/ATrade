<!-- Carbon tabs on Bits UI Tabs: the arrow keys, Home, and End move the focus and select the tab at the same time.
     `value` is the selected tab. The parent changes it in `onValueChange`, for example from the page address.
     The `panel` snippet is the one tab panel. It shows the content of the selected tab and stays in the page when
     the selected tab changes, so a chart in it is not created again.
     `size` "sm" gives the 32px tab line of a workbench panel. `lineEnd` puts content (for example the panel buttons)
     at the end of the tab line, in a line with the class `lineClass`. `itemLabel` renders the text of a tab, for
     example a name with a ChangeText; without it, the tab shows its `label`. `onSelectedTabClick` runs when the user
     clicks the tab that was already selected (or presses Enter or Space on it), for example to minimize a panel.
     The `items` are in a strip that scrolls sideways with its own track along its top edge (HorizontalScrollTrack), so a
     narrow tab line never cuts a tab and `lineEnd` stays visible. The selected tab scrolls into view in the strip. With
     `fixedItems`, those tabs stay visible after the strip. With `onCloseItem`, each tab of `items` has a Carbon
     dismissable close button; the Delete key on the focused tab does the same. -->
<script module lang="ts">
  export interface TabItem {
    value: string;
    label: string;
  }
</script>

<script lang="ts">
  import Close16 from '@carbon/icons/es/close/16.js';
  import { Tabs } from 'bits-ui';
  import type { Snippet } from 'svelte';
  import { computeScrollLeftToShow, HorizontalScrollTrack } from '#lib/foundation/scroll_region';
  import Icon from './Icon.svelte';

  interface Props {
    /** The accessible name of the tab list. */
    label: string;
    items: readonly TabItem[];
    value: string;
    onValueChange: (value: string) => void;
    contained?: boolean;
    size?: 'sm' | 'md';
    lineEnd?: Snippet;
    lineClass?: string;
    panelClass?: string;
    panel?: Snippet;
    itemLabel?: Snippet<[TabItem]>;
    onSelectedTabClick?: (value: string) => void;
    /** Tabs that never scroll away, after the scrolling strip of `items`. */
    fixedItems?: readonly TabItem[];
    /** Closes a tab of `items`. The parent removes it from `items`. */
    onCloseItem?: (value: string) => void;
  }

  const {
    label,
    items,
    value,
    onValueChange,
    contained = false,
    size = 'md',
    lineEnd,
    lineClass,
    panelClass,
    panel,
    itemLabel,
    onSelectedTabClick,
    fixedItems,
    onCloseItem,
  }: Props = $props();

  const stripId = $props.id();
  let strip: HTMLDivElement | undefined = $state();
  let stripContent: HTMLDivElement | undefined = $state();

  // The selected tab of the strip scrolls into view, for example a new backtest tab or a tab chosen with the keys.
  // Only the strip scrolls, not the panels around it. The close button of a dismissable tab shows with its tab.
  $effect(() => {
    const selected = value;
    const selectedTrigger = stripContent?.querySelector<HTMLElement>(`[data-tab-value="${CSS.escape(selected)}"]`);
    if (strip === undefined || stripContent === undefined || selectedTrigger === null || selectedTrigger === undefined) {
      return;
    }
    const contentLeftPixels = stripContent.getBoundingClientRect().left;
    const triggerRect = selectedTrigger.getBoundingClientRect();
    const closeButton = selectedTrigger.nextElementSibling;
    const itemRightPixels =
      closeButton?.classList.contains('cds--tabs__nav-item--close') === true
        ? closeButton.getBoundingClientRect().right
        : triggerRect.right;
    strip.scrollLeft = computeScrollLeftToShow({
      scrollLeftPixels: strip.scrollLeft,
      viewportWidthPixels: strip.getBoundingClientRect().width,
      itemLeftPixels: triggerRect.left - contentLeftPixels,
      itemWidthPixels: itemRightPixels - triggerRect.left,
    });
  });

  function closeWithKey(event: KeyboardEvent, itemValue: string): void {
    if (event.key === 'Delete' && onCloseItem !== undefined) {
      event.preventDefault();
      onCloseItem(itemValue);
    }
  }

  // The selected tab when the press starts. Bits UI selects a tab on focus, so at the click the pressed tab is always
  // selected.
  let selectedAtPress: string | null = null;

  function notePress(): void {
    selectedAtPress = value;
  }

  // A press that does not end in a click on the tab (the pointer moved away) is not a click on the selected tab.
  function forgetPress(): void {
    selectedAtPress = null;
  }

  function notePressKey(event: KeyboardEvent): void {
    if (event.key === 'Enter' || event.key === ' ') {
      selectedAtPress = value;
    }
  }

  function clickTab(itemValue: string): void {
    const wasSelected = selectedAtPress === itemValue;
    selectedAtPress = null;
    if (wasSelected) {
      onSelectedTabClick?.(itemValue);
    }
  }
</script>

{#snippet trigger(item: TabItem, isClosable: boolean)}
  <Tabs.Trigger
    value={item.value}
    class={['cds--tabs__nav-item', 'cds--tabs__nav-link', item.value === value && 'cds--tabs__nav-item--selected']}
    data-tab-value={item.value}
    onpointerdown={notePress}
    onpointercancel={forgetPress}
    onpointerleave={forgetPress}
    onkeydown={(event: KeyboardEvent) => {
      notePressKey(event);
      if (isClosable) {
        closeWithKey(event, item.value);
      }
    }}
    onclick={() => {
      clickTab(item.value);
    }}
  >
    <div class="cds--tabs__nav-item-label-wrapper">
      <span class="cds--tabs__nav-item-label">
        {#if itemLabel === undefined}{item.label}{:else}{@render itemLabel(item)}{/if}
      </span>
    </div>
  </Tabs.Trigger>
  {#if isClosable}
    <!-- Carbon dismissable tab: the close button follows its tab. Like Carbon, it is not in the Tab order; the Delete
         key on the focused tab closes it. -->
    <div class="cds--tabs__nav-item--close">
      <button
        type="button"
        class={['cds--tabs__nav-item--close-icon', item.value === value && 'cds--tabs__nav-item--close-icon--selected']}
        tabindex="-1"
        aria-label={`Close ${item.label}`}
        title={`Close ${item.label}`}
        onclick={() => onCloseItem?.(item.value)}
      >
        <Icon icon={Close16} />
      </button>
    </div>
  {/if}
{/snippet}

{#snippet tabList()}
  <div
    class={[
      'cds--tabs',
      contained && 'cds--tabs--contained',
      size === 'sm' && 'cds--layout--size-sm',
      onCloseItem !== undefined && 'cds--tabs--dismissable',
      'tabs--strip',
    ]}
  >
    <Tabs.List class="cds--tab--list" aria-label={label}>
      <div class="tab-strip" id={stripId} bind:this={strip}>
        <div class="tab-strip__content" bind:this={stripContent}>
          {#each items as item (item.value)}
            {@render trigger(item, onCloseItem !== undefined)}
          {/each}
        </div>
      </div>
      {#if fixedItems !== undefined && fixedItems.length > 0}
        <div class="tab-fixed">
          {#each fixedItems as item (item.value)}
            {@render trigger(item, false)}
          {/each}
        </div>
      {/if}
    </Tabs.List>
    <HorizontalScrollTrack {label} viewport={strip} content={stripContent} viewportId={stripId} class="tab-strip__track" />
  </div>
{/snippet}

<Tabs.Root {value} {onValueChange} activationMode="automatic">
  {#if lineEnd === undefined}
    {@render tabList()}
  {:else}
    <div class={lineClass}>
      {@render tabList()}
      {@render lineEnd()}
    </div>
  {/if}
  {#if panel !== undefined}
    <Tabs.Content {value} class={['cds--tab-content', panelClass]}>
      {@render panel()}
    </Tabs.Content>
  {/if}
</Tabs.Root>

<style>
  /* The strip of `items` takes the free width of the tab line and scrolls sideways; the fixed tabs and `lineEnd` keep
     their width.
     Carbon tokens only. */
  .tabs--strip {
    position: relative;
    flex: 1;
    min-inline-size: 0;
  }

  .tabs--strip :global(.cds--tab--list) {
    display: flex;
    inline-size: 100%;
    overflow: visible;
  }

  .tab-strip {
    flex: 1;
    min-inline-size: 0;
    overflow-x: auto;
    overflow-y: hidden;
    scrollbar-width: none;
  }

  .tab-strip::-webkit-scrollbar {
    display: none;
  }

  .tab-strip__content {
    display: flex;
    block-size: 100%;
    inline-size: max-content;
  }

  .tab-fixed {
    display: flex;
    flex: none;
    border-inline-start: 1px solid var(--cds-border-subtle-01);
  }

  /* The fixed tabs have no close button: the normal Carbon end padding. */
  .tabs--strip.cds--tabs--dismissable .tab-fixed :global(.cds--tabs__nav-link) {
    padding-inline-end: var(--cds-layout-density-padding-inline-local);
  }

  /* The track is along the top edge of the strip, so the selected tab line at the bottom stays visible. */
  .tabs--strip :global(.tab-strip__track) {
    position: absolute;
    inset-block-start: 0;
    inset-inline-start: 0;
    z-index: 1;
  }
</style>
