<!-- Carbon combo box on Bits UI Combobox. The user types, the page gives the candidates, ArrowUp and ArrowDown choose a
     candidate, Enter confirms it, and Escape closes the list. Bits UI does not filter: `items` are the shown candidates.
     The candidate list is in place (ContentStatic) in the Carbon list box and has its own visible scroll track. -->
<script lang="ts">
  import WarningFilled16 from '@carbon/icons/es/warning--filled/16.js';
  import ChevronDown16 from '@carbon/icons/es/chevron--down/16.js';
  import { Combobox } from 'bits-ui';
  import type { Snippet } from 'svelte';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { toComboboxClasses, toComboboxItemClasses, type ComboboxItem } from './combobox_classes';
  import Icon from './Icon.svelte';

  interface Props {
    label: string;
    items: ComboboxItem[];
    // The accessible name of the scrolling candidate list.
    listLabel: string;
    onInput: (text: string) => void;
    onSelect: (value: string) => void;
    placeholder?: string;
    listMaxHeight?: string;
    statusText?: string;
    invalidText?: string;
    // More content after the label of a candidate, for example a tag.
    itemContent?: Snippet<[ComboboxItem]>;
  }

  const {
    label,
    items,
    listLabel,
    onInput,
    onSelect,
    placeholder,
    listMaxHeight = '18rem',
    statusText,
    invalidText,
    itemContent,
  }: Props = $props();

  const inputId = $props.id();
  const messageId = `${inputId}-message`;
  let listElement: HTMLDivElement | null = $state(null);
  let menuElement: HTMLDivElement | null = $state(null);
  let open = $state(false);
  let value = $state('');
  let text = $state('');

  // New candidates open the list while the user is in the input. A change of `disabled` only does not open it.
  const itemValues = $derived(items.map((item) => item.value).join('\n'));
  $effect(() => {
    if (itemValues !== '' && document.activeElement?.id === inputId) {
      open = true;
    }
  });

  function confirmValue(confirmedValue: string): void {
    if (confirmedValue === '') {
      return;
    }
    // The combo box keeps no selection: the next Enter confirms a candidate again.
    value = '';
    onSelect(confirmedValue);
  }

  function readInput(event: Event & { currentTarget: HTMLInputElement }): void {
    text = event.currentTarget.value;
    onInput(text);
  }

  // Bits UI scrolls only its own viewport part. The list scrolls in ScrollRegion, so the component scrolls it.
  function showItem(itemValue: string): void {
    listElement?.querySelector(`[data-value="${CSS.escape(itemValue)}"]`)?.scrollIntoView({ block: 'nearest' });
  }

  // The scroll track of the list is outside the Bits UI listbox but inside the menu. A press on it keeps the list open.
  function keepOpenInMenu(event: PointerEvent): void {
    if (event.target instanceof Node && menuElement?.contains(event.target) === true) {
      event.preventDefault();
    }
  }

  function disabledAttribute(item: ComboboxItem): Record<string, string> {
    return item.disabled === true ? { disabled: '', 'aria-disabled': 'true' } : {};
  }
</script>

<div class="cds--list-box__wrapper">
  <label class="cds--label" for={inputId}>{label}</label>
  <Combobox.Root type="single" bind:open bind:value onValueChange={confirmValue} inputValue={text} {items}>
    <div
      class={toComboboxClasses({ open, hasItems: items.length > 0, invalid: invalidText !== undefined })}
      data-invalid={invalidText === undefined ? undefined : 'true'}
    >
      <div class="cds--list-box__field">
        <Combobox.Input id={inputId} oninput={readInput}>
          {#snippet child({ props })}
            <input
              {...props}
              class="cds--text-input"
              value={text}
              autocomplete="off"
              {placeholder}
              aria-describedby={statusText === undefined && invalidText === undefined ? undefined : messageId}
            />
          {/snippet}
        </Combobox.Input>
        {#if invalidText !== undefined}
          <Icon icon={WarningFilled16} class="cds--list-box__invalid-icon" />
        {/if}
        <Combobox.Trigger>
          {#snippet child({ props })}
            <button
              {...props}
              type="button"
              tabindex="-1"
              class={['cds--list-box__menu-icon', open && 'cds--list-box__menu-icon--open']}
              aria-label={open ? 'Close the list' : 'Open the list'}
            >
              <Icon icon={ChevronDown16} />
            </button>
          {/snippet}
        </Combobox.Trigger>
      </div>
      {#if items.length > 0}
        <Combobox.ContentStatic onInteractOutside={keepOpenInMenu}>
          {#snippet child({ props })}
            <div class="cds--list-box__menu candidate-menu" bind:this={menuElement}>
              <ScrollRegion label={listLabel} maxHeight={listMaxHeight}>
                <div {...props} bind:this={listElement}>
                  {#each items as item (item.value)}
                    <Combobox.Item
                      value={item.value}
                      label={item.label}
                      disabled={item.disabled}
                      onHighlight={() => {
                        showItem(item.value);
                      }}
                    >
                      {#snippet child({ props: itemProps, highlighted })}
                        <div
                          {...itemProps}
                          {...disabledAttribute(item)}
                          class={toComboboxItemClasses({ highlighted, disabled: item.disabled === true })}
                        >
                          <div class="cds--list-box__menu-item__option candidate-option">
                            <span>{item.label}</span>
                            {@render itemContent?.(item)}
                          </div>
                        </div>
                      {/snippet}
                    </Combobox.Item>
                  {/each}
                </div>
              </ScrollRegion>
            </div>
          {/snippet}
        </Combobox.ContentStatic>
      {/if}
    </div>
  </Combobox.Root>
  {#if invalidText !== undefined}
    <div class="cds--form-requirement" id={messageId} role="alert">{invalidText}</div>
  {:else if statusText !== undefined}
    <div class="cds--form__helper-text" id={messageId} role="status">{statusText}</div>
  {/if}
</div>

<style>
  /* The candidate list scrolls in ScrollRegion, which draws a visible track in every browser. */
  .candidate-menu {
    max-block-size: none;
    overflow: visible;
  }

  /* A candidate shows its label and, for example, a tag on one line. */
  .candidate-option {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--cds-spacing-03);
    font-variant-numeric: tabular-nums;
  }
</style>
