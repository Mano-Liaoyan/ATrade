<!-- Carbon tabs on Bits UI Tabs: the arrow keys, Home, and End move the focus and select the tab at the same time.
     `value` is the selected tab. The parent changes it in `onValueChange`, for example from the page address.
     The `panel` snippet is the one tab panel. It shows the content of the selected tab and stays in the page when
     the selected tab changes, so a chart in it is not created again.
     `size` "sm" gives the 32px tab line of a workbench panel. `lineEnd` puts content (for example the panel buttons)
     at the end of the tab line, in a line with the class `lineClass`. `itemLabel` renders the text of a tab, for
     example a name with a ChangeText; without it, the tab shows its `label`. `onSelectedTabClick` runs when the user
     clicks the tab that was already selected (or presses Enter or Space on it), for example to minimize a panel. -->
<script module lang="ts">
  export interface TabItem {
    value: string;
    label: string;
  }
</script>

<script lang="ts">
  import { Tabs } from 'bits-ui';
  import type { Snippet } from 'svelte';

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
  }: Props = $props();

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

{#snippet tabList()}
  <div class={['cds--tabs', contained && 'cds--tabs--contained', size === 'sm' && 'cds--layout--size-sm']}>
    <Tabs.List class="cds--tab--list" aria-label={label}>
      {#each items as item (item.value)}
        <Tabs.Trigger
          value={item.value}
          class={['cds--tabs__nav-item', 'cds--tabs__nav-link', item.value === value && 'cds--tabs__nav-item--selected']}
          onpointerdown={notePress}
          onpointercancel={forgetPress}
          onpointerleave={forgetPress}
          onkeydown={notePressKey}
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
      {/each}
    </Tabs.List>
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
