<!-- Carbon content switcher on Bits UI Tabs (list and triggers only, no panels). The arrow keys, Home, and End move
     the selection. The data-state of the Bits UI trigger becomes the Carbon selected class (carbon_state.ts). -->
<script module lang="ts">
  export interface ContentSwitcherItem<T extends string> {
    value: T;
    label: string;
    /** The accessible name when the visible label is a short name, for example "1 hour" for "1h". */
    accessibleLabel?: string;
  }
</script>

<script lang="ts" generics="T extends string">
  import { Tabs } from 'bits-ui';
  import { contentSwitcherButtonClasses, type BitsTabState } from './carbon_state';

  interface Props {
    // The accessible name of the tab list, for example "Side".
    label: string;
    items: ContentSwitcherItem<T>[];
    value: T;
    onValueChange: (value: T) => void;
    size?: 'sm' | 'md' | 'lg';
  }

  const { label, items, value, onValueChange, size = 'md' }: Props = $props();
</script>

<Tabs.Root
  bind:value={
    () => value,
    (selected: string) => {
      const item = items.find((candidate) => candidate.value === selected);
      if (item !== undefined) {
        onValueChange(item.value);
      }
    }
  }
>
  <Tabs.List aria-label={label}>
    {#snippet child({ props })}
      <!-- Carbon v11 reads the switcher height from the layout size class (cds--layout--size-<size>). -->
      <div
        {...props}
        class={[
          'cds--content-switcher',
          size !== 'md' && `cds--content-switcher--${size}`,
          size !== 'md' && `cds--layout--size-${size}`,
        ]}
      >
        {#each items as item (item.value)}
          <Tabs.Trigger value={item.value}>
            {#snippet child({ props: triggerProps })}
              <button
                {...triggerProps}
                type="button"
                aria-label={item.accessibleLabel}
                class={contentSwitcherButtonClasses(triggerProps['data-state'] as BitsTabState)}
              >
                <span class="cds--content-switcher__label">{item.label}</span>
              </button>
            {/snippet}
          </Tabs.Trigger>
        {/each}
      </div>
    {/snippet}
  </Tabs.List>
</Tabs.Root>
