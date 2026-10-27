<!-- Carbon dropdown on Bits UI Select. The keyboard opens it (Enter, Space, arrow keys), the arrow keys move the
     highlight, Enter selects, and Escape closes it. The open, highlighted, and selected states of Bits UI become the
     Carbon classes (carbon_state.ts). -->
<script module lang="ts">
  export interface SelectItem<T extends string> {
    value: T;
    label: string;
  }
</script>

<script lang="ts" generics="T extends string">
  import Checkmark16 from '@carbon/icons/es/checkmark/16.js';
  import ChevronDown16 from '@carbon/icons/es/chevron--down/16.js';
  import { Select } from 'bits-ui';
  import CarbonIcon from './CarbonIcon.svelte';
  import { dropdownClasses, dropdownMenuIconClasses, dropdownMenuItemClasses } from './carbon_state';

  interface Props {
    label: string;
    items: SelectItem<T>[];
    value: T;
    onValueChange: (value: T) => void;
    disabled?: boolean;
  }

  const uid = $props.id();
  const { label, items, value, onValueChange, disabled = false }: Props = $props();

  let open = $state(false);
  const triggerId = `select-${uid}`;
  const selectedLabel = $derived(items.find((item) => item.value === value)?.label ?? '');
</script>

<div class="cds--dropdown__wrapper cds--list-box__wrapper">
  <label for={triggerId} class="cds--label">{label}</label>
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
    <div class={dropdownClasses({ open, disabled })}>
      <Select.Trigger id={triggerId}>
        {#snippet child({ props })}
          <button {...props} type="button" class="cds--list-box__field">
            <span class="cds--list-box__label">{selectedLabel}</span>
            <div class={dropdownMenuIconClasses(open)}>
              <CarbonIcon icon={ChevronDown16} />
            </div>
          </button>
        {/snippet}
      </Select.Trigger>
      <Select.ContentStatic>
        {#snippet child({ props })}
          <div {...props} class="cds--list-box__menu">
            {#each items as item (item.value)}
              <Select.Item value={item.value} label={item.label}>
                {#snippet child({ props: itemProps, selected, highlighted })}
                  <div {...itemProps} class={dropdownMenuItemClasses({ highlighted, selected })}>
                    <div class="cds--list-box__menu-item__option">
                      {item.label}
                      {#if selected}
                        <CarbonIcon icon={Checkmark16} class="cds--list-box__menu-item__selected-icon" />
                      {/if}
                    </div>
                  </div>
                {/snippet}
              </Select.Item>
            {/each}
          </div>
        {/snippet}
      </Select.ContentStatic>
    </div>
  </Select.Root>
</div>
