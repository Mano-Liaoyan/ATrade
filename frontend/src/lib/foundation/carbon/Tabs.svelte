<!-- Carbon tabs on Bits UI Tabs: the arrow keys, Home, and End move the focus and select the tab at the same time.
     `value` is the selected tab. The parent changes it in `onValueChange`, for example from the page address.
     The `panel` snippet is the one tab panel. It shows the content of the selected tab and stays in the page when
     the selected tab changes, so a chart in it is not created again.
     `size` "sm" gives the 32px tab line of a workbench panel. `lineEnd` puts content (for example the panel buttons)
     at the end of the tab line, in a line with the class `lineClass`. -->
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
  }: Props = $props();
</script>

{#snippet tabList()}
  <div class={['cds--tabs', contained && 'cds--tabs--contained', size === 'sm' && 'cds--layout--size-sm']}>
    <Tabs.List class="cds--tab--list" aria-label={label}>
      {#each items as item (item.value)}
        <Tabs.Trigger
          value={item.value}
          class={['cds--tabs__nav-item', 'cds--tabs__nav-link', item.value === value && 'cds--tabs__nav-item--selected']}
        >
          <div class="cds--tabs__nav-item-label-wrapper">
            <span class="cds--tabs__nav-item-label">{item.label}</span>
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
