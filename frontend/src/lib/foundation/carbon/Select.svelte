<!-- Carbon dropdown on Bits UI Select. The keyboard opens it (Enter, Space, arrow keys), the arrow keys move the
     highlight, Enter selects, and Escape closes it. The open, highlighted, and selected states of Bits UI become the
     Carbon classes (carbon_state.ts). `size` "sm" gives the 32px field of a toolbar line, and `hideLabel` keeps the
     label only for screen readers when the layout names the field. A label that the field cuts shows in full in a
     native tooltip. The list is at least as wide as the field and wide enough for its longest label. -->
<script module lang="ts">
  export interface SelectItem<T extends string> {
    value: T;
    label: string;
    // A Carbon tag after the label, for example "Discarded" after a version number.
    tag?: string;
  }
</script>

<script lang="ts" generics="T extends string">
  import Checkmark16 from '@carbon/icons/es/checkmark/16.js';
  import ChevronDown16 from '@carbon/icons/es/chevron--down/16.js';
  import { Select } from 'bits-ui';
  import Icon from './Icon.svelte';
  import Tag from './Tag.svelte';
  import { dropdownClasses, dropdownMenuIconClasses, dropdownMenuItemClasses } from './carbon_state';

  interface Props {
    label: string;
    items: SelectItem<T>[];
    value: T;
    onValueChange: (value: T) => void;
    disabled?: boolean;
    // The text of the trigger while no item is selected.
    placeholder?: string;
    size?: 'sm' | 'md';
    hideLabel?: boolean;
    // Why the Select is disabled: the native tooltip of the field, and its accessible description.
    disabledReason?: string | null;
  }

  const uid = $props.id();
  const {
    label,
    items,
    value,
    onValueChange,
    disabled = false,
    placeholder = '',
    size = 'md',
    hideLabel = false,
    disabledReason = null,
  }: Props = $props();

  let open = $state(false);
  let isLabelCut = $state(false);
  const triggerId = `select-${uid}`;
  const reasonId = `select-reason-${uid}`;
  const selectedItem = $derived(items.find((item) => item.value === value));
  const fieldText = $derived(selectedItem?.label ?? placeholder);
  const fieldTitle = $derived(
    disabled && disabledReason !== null ? disabledReason : isLabelCut ? fieldText : undefined,
  );

  // Measured when the pointer comes to the field, so a resize of the column needs no observer.
  function measureLabel(event: PointerEvent): void {
    const label = (event.currentTarget as HTMLElement).querySelector('.cds--list-box__label');
    isLabelCut = label !== null && label.scrollWidth > label.clientWidth;
  }
</script>

<!-- The tooltip is on the wrapper too: a disabled button gets no pointer events in all browsers. -->
<div class="cds--dropdown__wrapper cds--list-box__wrapper" title={fieldTitle}>
  <label for={triggerId} class={['cds--label', hideLabel && 'cds--visually-hidden']}>{label}</label>
  {#if disabled && disabledReason !== null}
    <span id={reasonId} class="cds--visually-hidden">{disabledReason}</span>
  {/if}
  <Select.Root
    type="single"
    bind:open
    {items}
    {disabled}
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
    <div class={[...dropdownClasses({ open, disabled }), size === 'sm' && 'cds--dropdown--sm cds--list-box--sm']}>
      <Select.Trigger id={triggerId}>
        {#snippet child({ props })}
          <button
            {...props}
            type="button"
            class="cds--list-box__field"
            onpointerenter={measureLabel}
            aria-describedby={disabled && disabledReason !== null ? reasonId : undefined}
          >
            <span class="cds--list-box__label">{fieldText}</span>
            {#if selectedItem?.tag !== undefined}
              <Tag label={selectedItem.tag} size="sm" />
            {/if}
            <div class={dropdownMenuIconClasses(open)}>
              <Icon icon={ChevronDown16} />
            </div>
          </button>
        {/snippet}
      </Select.Trigger>
      <!-- Floating and fixed, not static: a scrolling parent (for example the content of a Dialog) does not cut the list. -->
      <Select.Content side="bottom" align="start" sideOffset={0} strategy="fixed">
        {#snippet child({ props, wrapperProps })}
          <div {...wrapperProps}>
            <div {...props} class="cds--list-box__menu floating-menu">
              {#each items as item (item.value)}
                <Select.Item value={item.value} label={item.label}>
                  {#snippet child({ props: itemProps, selected, highlighted })}
                    <div {...itemProps} class={dropdownMenuItemClasses({ highlighted, selected })}>
                      <div class="cds--list-box__menu-item__option">
                        {item.label}
                        {#if item.tag !== undefined}
                          <Tag label={item.tag} size="sm" />
                        {/if}
                        {#if selected}
                          <Icon icon={Checkmark16} class="cds--list-box__menu-item__selected-icon" />
                        {/if}
                      </div>
                    </div>
                  {/snippet}
                </Select.Item>
              {/each}
            </div>
          </div>
        {/snippet}
      </Select.Content>
    </div>
  </Select.Root>
</div>

<style>
  /* As in MenuButton.svelte: Bits UI places the floating wrapper, so the Carbon offsets go. The list is at least as wide
     as the field and as wide as its longest label, but not wider than the viewport. Bits UI moves it into the viewport. */
  .floating-menu {
    position: relative;
    inset: auto;
    min-inline-size: var(--bits-select-anchor-width);
    inline-size: max-content;
    max-inline-size: calc(100vw - 2 * var(--cds-spacing-05));
  }

  /* Carbon has no tag inside a dropdown item. The tag stays on the line of the label. */
  .cds--list-box__field :global(.cds--tag),
  .cds--list-box__menu-item__option :global(.cds--tag) {
    margin-block: 0;
    margin-inline: var(--cds-spacing-03) 0;
    vertical-align: middle;
  }

  /* The tag keeps its width. The label takes the rest of the field and gets the ellipsis. */
  .cds--list-box__field :global(.cds--tag) {
    flex: none;
  }

  .cds--list-box__field:has(:global(.cds--tag)) .cds--list-box__label {
    flex: 0 1 auto;
  }
</style>
