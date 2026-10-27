<!-- The command palette: a header search icon button and a Carbon modal with a large Carbon search field and Carbon
     contained lists, on Bits UI Dialog and Command. Ctrl K or Cmd K opens and closes it on each page, and Escape closes
     it. The text filters the commands, Arrow Up and Arrow Down move the highlight, and Enter runs the command. -->
<script lang="ts">
  import Search16 from '@carbon/icons/es/search/16.js';
  import Search20 from '@carbon/icons/es/search/20.js';
  import { Command, Dialog, mergeProps } from 'bits-ui';
  import { Icon, Tooltip } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { isCommandPaletteShortcut, type PaletteCommand, type PaletteCommandGroup } from './command_palette';

  interface Props {
    groups: PaletteCommandGroup[];
    /** Called each time the palette opens, for example to read the newest watchlist. */
    onOpen?: () => void;
  }

  const { groups, onOpen }: Props = $props();

  const OPEN_LABEL = 'Open command palette';

  let open = $state(false);
  let commandText = $state('');

  function changeOpen(nextOpen: boolean): void {
    if (nextOpen && !open) {
      commandText = '';
      onOpen?.();
    }
    open = nextOpen;
  }

  function toggleWithShortcut(event: KeyboardEvent): void {
    if (isCommandPaletteShortcut(event)) {
      event.preventDefault();
      changeOpen(!open);
    }
  }

  function runCommand(command: PaletteCommand): void {
    open = false;
    command.run();
  }
</script>

<svelte:window onkeydown={toggleWithShortcut} />

<Tooltip text={OPEN_LABEL} align="bottom-end">
  {#snippet trigger({ props })}
    <button
      {...mergeProps(props, {
        onclick: () => {
          changeOpen(true);
        },
      })}
      type="button"
      class="cds--header__action cds--btn--icon-only"
      aria-label={OPEN_LABEL}
    >
      <Icon icon={Search20} />
    </button>
  {/snippet}
</Tooltip>

<Dialog.Root bind:open={() => open, changeOpen}>
  <Dialog.Portal>
    {#if open}
      <!-- Carbon shows the modal only with is-visible. A click on the overlay is outside the content and closes it. -->
      <div class="cds--modal is-visible command-palette-overlay">
        <Dialog.Content>
          {#snippet child({ props })}
            <div {...props} class="cds--modal-container cds--modal-container--sm">
              <Dialog.Title>
                {#snippet child({ props: titleProps })}
                  <h2 {...titleProps} class="cds--visually-hidden">Command palette</h2>
                {/snippet}
              </Dialog.Title>
              <!-- vimBindings is off: with it, Bits UI takes Ctrl K to move the highlight. -->
              <Command.Root label="Commands" vimBindings={false} loop>
                <div class="cds--search cds--search--lg" role="search">
                  <div class="cds--search-magnifier" aria-hidden="true">
                    <Icon icon={Search16} class="cds--search-magnifier-icon" />
                  </div>
                  <Command.Input class="cds--search-input" bind:value={commandText} placeholder="Command" />
                </div>
                <ScrollRegion label="Commands" maxHeight="50vh">
                  <Command.List>
                    <Command.Viewport>
                      <Command.Empty>
                        {#snippet child({ props: emptyProps })}
                          <p {...emptyProps} class="command-palette-empty">No results</p>
                        {/snippet}
                      </Command.Empty>
                      {#each groups as group (group.heading)}
                        <Command.Group value={group.heading} class="cds--contained-list cds--contained-list--on-page">
                          <Command.GroupHeading class="cds--contained-list__header">
                            <span class="cds--contained-list__label">{group.heading}</span>
                          </Command.GroupHeading>
                          <Command.GroupItems>
                            {#each group.commands as command (command.label)}
                              <Command.Item
                                value={command.label}
                                keywords={command.keywords}
                                onSelect={() => {
                                  runCommand(command);
                                }}
                              >
                                {#snippet child({ props: itemProps })}
                                  <div class="cds--contained-list-item cds--contained-list-item--clickable" role="none">
                                    <div {...itemProps} class="cds--contained-list-item__content command-palette-item">
                                      {command.label}
                                    </div>
                                  </div>
                                {/snippet}
                              </Command.Item>
                            {/each}
                          </Command.GroupItems>
                        </Command.Group>
                      {/each}
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
  /* The palette stays at the same height while the filter changes the list. */
  .command-palette-overlay {
    align-items: flex-start;
    padding-block-start: var(--cds-spacing-13);
  }

  /* Carbon has a hover style only. The highlighted command of the keyboard gets the same color. */
  .command-palette-item:global([data-selected]) {
    background-color: var(--cds-layer-hover);
  }

  .command-palette-empty {
    margin: 0;
    padding: var(--cds-spacing-05);
    font-size: var(--cds-body-01-font-size);
    line-height: var(--cds-body-01-line-height);
    letter-spacing: var(--cds-body-01-letter-spacing);
    color: var(--cds-text-secondary);
  }
</style>
