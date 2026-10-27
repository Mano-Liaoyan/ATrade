<!-- Carbon overflow menu on Bits UI DropdownMenu: the keyboard opens it and moves through its items, and Escape closes
     it. The menu goes under <body>, so a scroll region or a table cannot clip it. A disabled item stays in the menu,
     and its label says why it is disabled. -->
<script module lang="ts">
  export interface OverflowMenuItem {
    label: string;
    disabled?: boolean;
    danger?: boolean;
    onSelect: () => void;
  }
</script>

<script lang="ts">
  import OverflowMenuVertical16 from '@carbon/icons/es/overflow-menu--vertical/16.js';
  import { DropdownMenu } from 'bits-ui';
  import Icon from './Icon.svelte';

  interface Props {
    // The accessible name of the trigger button, for example "Actions for order 418".
    label: string;
    items: OverflowMenuItem[];
    // The Carbon size of the trigger and the items. In a data table, use the size of the table rows.
    size?: 'xs' | 'sm' | 'md' | 'lg';
  }

  const { label, items, size = 'md' }: Props = $props();

  let open = $state(false);
</script>

<DropdownMenu.Root bind:open>
  <DropdownMenu.Trigger>
    {#snippet child({ props })}
      <button {...props} type="button" class={['cds--overflow-menu', `cds--layout--size-${size}`, open && 'cds--overflow-menu--open']} aria-label={label}>
        <Icon icon={OverflowMenuVertical16} class="cds--overflow-menu__icon" />
      </button>
    {/snippet}
  </DropdownMenu.Trigger>
  <DropdownMenu.Portal>
    <!-- Carbon puts the menu below the trigger with its end edges in line (cds--overflow-menu--flip). -->
    <DropdownMenu.Content side="bottom" align="end" sideOffset={0}>
      {#snippet child({ props, wrapperProps })}
        <div {...wrapperProps}>
          <ul
            {...props}
            class={[
              'cds--overflow-menu-options',
              'cds--overflow-menu-options--open',
              'cds--overflow-menu--flip',
              `cds--layout--size-${size}`,
              'floating-options',
            ]}
            data-floating-menu-direction={props['data-side']}
          >
            {#each items as item (item.label)}
              <li
                class={[
                  'cds--overflow-menu-options__option',
                  item.danger === true && 'cds--overflow-menu-options__option--danger',
                  item.disabled === true && 'cds--overflow-menu-options__option--disabled',
                ]}
                role="none"
              >
                <DropdownMenu.Item disabled={item.disabled === true} textValue={item.label} onSelect={item.onSelect}>
                  {#snippet child({ props: itemProps })}
                    <button {...itemProps} type="button" class="cds--overflow-menu-options__btn floating-option-button">
                      <div class="cds--overflow-menu-options__option-content">{item.label}</div>
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
    /* An item label is never cut: the menu is as wide as its longest label, and at least the Carbon menu width. */
    /* 10rem is Carbon $spacing-13, the width that Carbon gives the menu. */
    min-inline-size: 10rem;
    inline-size: max-content;
  }

  .floating-option-button {
    max-inline-size: none;
  }
</style>
