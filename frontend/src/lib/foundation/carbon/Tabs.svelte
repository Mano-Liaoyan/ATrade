<!-- Carbon tabs on Bits UI Tabs: the arrow keys, Home, and End move the focus and select the tab at the same time.
     `value` is the selected tab. The parent changes it in `onValueChange`, for example from the page address.
     The `panel` snippet is the one tab panel. It shows the content of the selected tab and stays in the page when
     the selected tab changes, so a chart in it is not created again. -->
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
    panel?: Snippet;
  }

  const { label, items, value, onValueChange, contained = false, panel }: Props = $props();
</script>

<Tabs.Root {value} {onValueChange} activationMode="automatic">
  <div class={['cds--tabs', contained && 'cds--tabs--contained']}>
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
  {#if panel !== undefined}
    <Tabs.Content {value} class="cds--tab-content">
      {@render panel()}
    </Tabs.Content>
  {/if}
</Tabs.Root>
