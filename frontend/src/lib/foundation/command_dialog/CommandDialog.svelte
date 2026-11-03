<!-- A Carbon modal with a title, a large Carbon search field, and one Carbon contained list, on Bits UI Dialog and
     Command. The text filters the items (the label and the keywords), Arrow Up and Arrow Down move the highlight, and
     Enter or a click selects the highlighted item and closes the dialog. Escape closes it without a choice. The list
     has no groups. The items keep their order. An item can have an icon button at its end (`action`, Carbon contained
     list item action). The button is in the tab order, and a click on it calls `onAction` and does not select. -->
<script lang="ts">
  import Close20 from '@carbon/icons/es/close/20.js';
  import Search16 from '@carbon/icons/es/search/16.js';
  import { Command, Dialog } from 'bits-ui';
  import { buttonClasses, Icon, IconButton } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import type { CommandDialogItem } from './command_dialog';

  interface Props {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    title: string;
    /** The placeholder and the accessible name of the search field. */
    searchLabel: string;
    items: CommandDialogItem[];
    onSelect: (value: string) => void;
    /** A click on the action button of the item with this value. */
    onAction?: (value: string) => void;
  }

  const { open, onOpenChange, title, searchLabel, items, onSelect, onAction = () => undefined }: Props = $props();

  // The modal title is an h2: the dialog is outside the page outline, and the page has its own h1.
  const TITLE_LEVEL = 2;

  let searchText = $state('');
  let searchInput: HTMLInputElement | null = $state(null);

  // The search field gets the focus when the dialog opens, not the Close button before it.
  function focusSearch(event: Event): void {
    event.preventDefault();
    searchInput?.focus();
  }

  function changeOpen(nextOpen: boolean): void {
    if (nextOpen && !open) {
      searchText = '';
    }
    onOpenChange(nextOpen);
  }

  function selectItem(item: CommandDialogItem): void {
    if (item.disabledText !== undefined) {
      return;
    }
    onOpenChange(false);
    onSelect(item.value);
  }

  $effect(() => {
    if (open) {
      searchText = '';
    }
  });
</script>

<Dialog.Root {open} onOpenChange={changeOpen}>
  <Dialog.Portal>
    {#if open}
      <div class="cds--modal is-visible command-dialog-overlay">
        <Dialog.Content onOpenAutoFocus={focusSearch}>
          {#snippet child({ props })}
            <div {...props} class="cds--modal-container cds--modal-container--sm command-dialog-container">
              <div class="cds--modal-header">
                <Dialog.Title level={TITLE_LEVEL}>
                  {#snippet child({ props: titleProps })}
                    <h2 {...titleProps} class="cds--modal-header__heading">{title}</h2>
                  {/snippet}
                </Dialog.Title>
                <div class="cds--modal-close-button">
                  <Dialog.Close>
                    {#snippet child({ props: closeProps })}
                      <button
                        {...closeProps}
                        type="button"
                        class={['cds--modal-close', ...buttonClasses({ kind: 'ghost', size: 'lg', iconOnly: true })]}
                        aria-label="Close"
                      >
                        <Icon icon={Close20} class="cds--modal-close__icon" />
                      </button>
                    {/snippet}
                  </Dialog.Close>
                </div>
              </div>
              <Command.Root label={title} vimBindings={false} loop>
                <div class="cds--search cds--search--lg" role="search">
                  <div class="cds--search-magnifier" aria-hidden="true">
                    <Icon icon={Search16} class="cds--search-magnifier-icon" />
                  </div>
                  <Command.Input class="cds--search-input" bind:ref={searchInput} bind:value={searchText} placeholder={searchLabel} aria-label={searchLabel} />
                </div>
                <ScrollRegion label={title} maxHeight="40vh">
                  <Command.List>
                    <Command.Viewport>
                      <Command.Empty>
                        {#snippet child({ props: emptyProps })}
                          <p {...emptyProps} class="command-dialog-empty">No results</p>
                        {/snippet}
                      </Command.Empty>
                      <div class="cds--contained-list cds--contained-list--on-page">
                        {#each items as item (item.value)}
                          <Command.Item
                            value={item.label}
                            keywords={item.keywords}
                            disabled={item.disabledText !== undefined}
                            onSelect={() => {
                              selectItem(item);
                            }}
                          >
                            {#snippet child({ props: itemProps })}
                              <div
                                class={[
                                  'cds--contained-list-item',
                                  item.disabledText === undefined && 'cds--contained-list-item--clickable',
                                  item.action !== undefined && 'cds--contained-list-item--with-action',
                                ]}
                                role="none"
                              >
                                <div {...itemProps} class="cds--contained-list-item__content command-dialog-item">
                                  <span>{item.label}</span>
                                  {#if item.disabledText !== undefined}
                                    <span class="command-dialog-disabled-text">{item.disabledText}</span>
                                  {:else if item.detail !== undefined}
                                    <span class="command-dialog-detail">{item.detail}</span>
                                  {/if}
                                </div>
                                {#if item.action !== undefined}
                                  <div class="cds--contained-list-item__action command-dialog-action">
                                    <IconButton
                                      label={item.action.label}
                                      icon={item.action.icon}
                                      align="left"
                                      floatingTooltip
                                      onclick={() => {
                                        onAction(item.value);
                                      }}
                                    />
                                  </div>
                                {/if}
                              </div>
                            {/snippet}
                          </Command.Item>
                        {/each}
                      </div>
                    </Command.Viewport>
                  </Command.List>
                </ScrollRegion>
              </Command.Root>
            </div>
          {/snippet}
        </Dialog.Content>
      </div>
    {/if}
  </Dialog.Portal>
</Dialog.Root>

<style>
  /* The dialog stays at the same height while the filter changes the list. */
  .command-dialog-overlay {
    align-items: flex-start;
    padding-block-start: var(--cds-spacing-13);
  }

  /* The header, the search field, and the list (at most 40vh, it scrolls in its own track) take their own height. */
  .command-dialog-container {
    max-block-size: none;
  }

  .command-dialog-item {
    display: flex;
    gap: var(--cds-spacing-05);
    justify-content: space-between;
  }

  /* Carbon has a hover style only. The highlighted item of the keyboard gets the same color. */
  .command-dialog-item:global([data-selected]) {
    background-color: var(--cds-layer-hover);
  }

  .command-dialog-item:global([data-disabled]) {
    color: var(--cds-text-disabled);
    cursor: not-allowed;
  }

  /* The action button is in the middle of the item height, at its end. */
  .command-dialog-action {
    inset-block-end: 0;
    align-items: center;
    padding-inline-end: var(--cds-spacing-03);
  }

  .command-dialog-detail {
    font-family: var(--cds-code-01-font-family, 'IBM Plex Mono', monospace);
    color: var(--cds-text-secondary);
  }

  .command-dialog-disabled-text {
    color: var(--cds-text-secondary);
  }

  .command-dialog-empty {
    margin: 0;
    padding: var(--cds-spacing-05);
    font-size: var(--cds-body-01-font-size);
    line-height: var(--cds-body-01-line-height);
    letter-spacing: var(--cds-body-01-letter-spacing);
    color: var(--cds-text-secondary);
  }
</style>
