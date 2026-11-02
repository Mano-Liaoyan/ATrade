<!-- A Carbon v11 context menu (the Menu of @carbon/react, `cds--menu`) on Bits UI ContextMenu. A right-click, the
     ContextMenu key, or Shift+F10 in the area opens it at the pointer. The menu is for the row under the pointer: the
     nearest element with `data-context-key` gives its key to `readItems`. Without such an element, or without items,
     no menu opens. The keyboard moves through the items, and Escape closes the menu. An item with `divider` has a
     divider line above it; a `danger` item has the Carbon danger color. -->
<script module lang="ts">
  export interface ContextMenuItem {
    label: string;
    onSelect: () => void;
    divider?: boolean;
    danger?: boolean;
  }
</script>

<script lang="ts">
  import { ContextMenu } from 'bits-ui';
  import type { Snippet } from 'svelte';

  // The attribute of the element that the menu is for, for example a list row.
  const CONTEXT_KEY_ATTRIBUTE = 'data-context-key';

  interface Props {
    /** The accessible name of the menu, for example "Backtest #12". It comes from the key. */
    readLabel: (key: string) => string;
    readItems: (key: string) => ContextMenuItem[];
    children: Snippet;
  }

  const { readLabel, readItems, children }: Props = $props();

  let open = $state(false);
  let label = $state('');
  let items: ContextMenuItem[] = $state([]);

  // Runs before the Bits UI trigger handler. A prevented event opens neither this menu nor the menu of the browser.
  function readTarget(event: MouseEvent): void {
    const target = event.target instanceof Element ? event.target.closest(`[${CONTEXT_KEY_ATTRIBUTE}]`) : null;
    const key = target?.getAttribute(CONTEXT_KEY_ATTRIBUTE) ?? null;
    items = key === null ? [] : readItems(key);
    if (key === null || items.length === 0) {
      event.preventDefault();
      return;
    }
    label = readLabel(key);
  }
</script>

<ContextMenu.Root bind:open>
  <ContextMenu.Trigger oncontextmenu={readTarget}>
    {#snippet child({ props })}
      <div {...props} class="context-area">
        {@render children()}
      </div>
    {/snippet}
  </ContextMenu.Trigger>
  <ContextMenu.Portal>
    <ContextMenu.Content>
      {#snippet child({ props, wrapperProps })}
        <!-- Above a Dialog (Carbon modal 9000), as the Carbon list box menu (9100). -->
        <div {...wrapperProps} style:z-index="9100">
          <ul {...props} class="cds--menu cds--menu--sm cds--menu--open cds--menu--shown floating-menu" aria-label={label}>
            {#each items as item (item.label)}
              {#if item.divider === true}
                <ContextMenu.Separator>
                  {#snippet child({ props: separatorProps })}
                    <li {...separatorProps} class="cds--menu-item-divider"></li>
                  {/snippet}
                </ContextMenu.Separator>
              {/if}
              <ContextMenu.Item textValue={item.label} onSelect={item.onSelect}>
                {#snippet child({ props: itemProps })}
                  <li {...itemProps} class={['cds--menu-item', item.danger === true && 'cds--menu-item--danger']}>
                    <div class="cds--menu-item__label">{item.label}</div>
                  </li>
                {/snippet}
              </ContextMenu.Item>
            {/each}
          </ul>
        </div>
      {/snippet}
    </ContextMenu.Content>
  </ContextMenu.Portal>
</ContextMenu.Root>

<style>
  /* The area fills the list region, so a right-click on each row reaches it. */
  .context-area {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-block-size: 0;
  }

  /* Bits UI places the floating wrapper, so the fixed Carbon position goes. */
  .floating-menu {
    position: relative;
    inset: auto;
  }
</style>
