<!-- A Carbon ghost icon-only button (size sm, like IconButton) with a Carbon tooltip, that opens a Carbon overflow menu
     on Bits UI DropdownMenu. The keyboard opens the menu and moves through its items, and Escape closes it. `label` is
     the accessible name and the tooltip text. `itemContent` renders the content of an item, for example a status icon
     and a name; without it, the item shows its `label`. An item with `divider` has a divider line above it.
     After an item is selected, the focus does not go back to the button: `onSelect` moves it, for example to the tab
     that the item opened (the button can go away after the select). Escape and a click outside return the focus to
     the button. The menu goes under <body>, above a Dialog. -->
<script module lang="ts">
  export interface IconMenuItem {
    value: string;
    /** The text of the item, and its text for typeahead. */
    label: string;
    divider?: boolean;
    onSelect: () => void;
  }
</script>

<script lang="ts">
  import { DropdownMenu } from 'bits-ui';
  import type { Snippet } from 'svelte';
  import type { CarbonIconNode } from './carbon_icon';
  import Icon from './Icon.svelte';
  import Tooltip from './Tooltip.svelte';

  interface Props {
    label: string;
    icon: Pick<CarbonIconNode, 'attrs' | 'content'>;
    items: IconMenuItem[];
    itemContent?: Snippet<[IconMenuItem]>;
  }

  const { label, icon, items, itemContent }: Props = $props();

  let open = $state(false);
  // True between an item select and the close of the menu: the close does not focus the button.
  let isSelecting = false;

  function keepFocusAfterSelect(event: Event): void {
    if (isSelecting) {
      isSelecting = false;
      event.preventDefault();
    }
  }
</script>

<DropdownMenu.Root bind:open>
  <Tooltip text={label}>
    {#snippet trigger({ props: tooltipProps })}
      <DropdownMenu.Trigger {...tooltipProps}>
        {#snippet child({ props })}
          <button
            {...props}
            type="button"
            class="cds--btn cds--btn--ghost cds--btn--sm cds--layout--size-sm cds--btn--icon-only"
            aria-label={label}
          >
            <Icon {icon} class="cds--btn__icon" />
          </button>
        {/snippet}
      </DropdownMenu.Trigger>
    {/snippet}
  </Tooltip>
  <DropdownMenu.Portal>
    <DropdownMenu.Content side="bottom" align="start" sideOffset={0} onCloseAutoFocus={keepFocusAfterSelect}>
      {#snippet child({ props, wrapperProps })}
        <!-- Above a Dialog (Carbon modal 9000), as the Carbon list box menu (9100): the Portal puts the menu outside it,
             and the fixed wrapper is its own stacking context. -->
        <div {...wrapperProps} style:z-index="9100">
          <ul {...props} class="cds--overflow-menu-options cds--overflow-menu-options--open cds--layout--size-sm floating-options">
            {#each items as item (item.value)}
              <li class={['cds--overflow-menu-options__option', item.divider === true && 'cds--overflow-menu--divider']} role="none">
                <DropdownMenu.Item
                  textValue={item.label}
                  onSelect={() => {
                    isSelecting = true;
                    item.onSelect();
                  }}
                >
                  {#snippet child({ props: itemProps })}
                    <button {...itemProps} type="button" class="cds--overflow-menu-options__btn floating-option-button">
                      <div class="cds--overflow-menu-options__option-content">
                        {#if itemContent === undefined}{item.label}{:else}{@render itemContent(item)}{/if}
                      </div>
                    </button>
                  {/snippet}
                </DropdownMenu.Item>
              </li>
            {/each}
          </ul>
        </div>
      {/snippet}
    </DropdownMenu.Content>
  </DropdownMenu.Portal>
</DropdownMenu.Root>

<style>
  /* Carbon places the menu with its own absolute offsets. Bits UI places the floating wrapper, so the offsets go. */
  .floating-options {
    position: relative;
    inset: auto;
    /* An item label is never cut: the menu is as wide as its longest label, and at least the Carbon menu width
       ($spacing-13). */
    min-inline-size: var(--cds-spacing-13);
    inline-size: max-content;
  }

  .floating-option-button {
    max-inline-size: none;
  }
</style>
