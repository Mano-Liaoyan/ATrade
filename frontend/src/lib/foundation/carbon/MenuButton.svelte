<!-- A ghost button with a text that opens a Carbon menu, on Bits UI DropdownMenu. The keyboard opens it and moves
     through its items, and Escape closes it. The menu uses the Carbon overflow menu options; an item with `divider`
     has a divider line above it. `onSelect` gets the trigger element, so the caller can open a popover at it. -->
<script module lang="ts">
  export interface MenuButtonItem {
    label: string;
    divider?: boolean;
    onSelect: (trigger: HTMLElement | null) => void;
  }
</script>

<script lang="ts">
  import { DropdownMenu } from 'bits-ui';
  import { buttonClasses } from './carbon_state';

  interface Props {
    label: string;
    items: MenuButtonItem[];
  }

  const { label, items }: Props = $props();

  let open = $state(false);
  let trigger: HTMLElement | null = $state(null);
</script>

<DropdownMenu.Root bind:open>
  <DropdownMenu.Trigger bind:ref={trigger}>
    {#snippet child({ props })}
      <button {...props} type="button" class={buttonClasses({ kind: 'ghost', size: 'sm' })}>{label}</button>
    {/snippet}
  </DropdownMenu.Trigger>
  <DropdownMenu.Portal>
    <DropdownMenu.Content side="bottom" align="start" sideOffset={0}>
      {#snippet child({ props, wrapperProps })}
        <div {...wrapperProps}>
          <ul {...props} class="cds--overflow-menu-options cds--overflow-menu-options--open cds--layout--size-sm floating-options">
            {#each items as item (item.label)}
              <li class={['cds--overflow-menu-options__option', item.divider === true && 'cds--overflow-menu--divider']} role="none">
                <DropdownMenu.Item
                  textValue={item.label}
                  onSelect={() => {
                    item.onSelect(trigger);
                  }}
                >
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
  /* As in OverflowMenu.svelte: Bits UI places the floating wrapper, so the Carbon offsets go. */
  .floating-options {
    position: relative;
    inset: auto;
    min-inline-size: var(--cds-spacing-13);
    inline-size: max-content;
  }

  .floating-option-button {
    max-inline-size: none;
  }
</style>
