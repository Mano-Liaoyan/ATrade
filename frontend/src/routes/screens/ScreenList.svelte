<!-- The screen list of the screen workbench (the body of the "Screens" side column): each row has the name and the
     market. The open screen expands to its recent runs (time and instrument count). A click on a run opens its screen
     result (docs/architecture/screen.md section 24.10). A failed "New screen" shows its reason above the list. A
     right-click on a screen opens its context menu: "Open in new tab" and "Delete screen" (after a danger dialog). -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { goto } from '$app/navigation';
  import { ContextMenu, Dialog, InlineNotification, type ContextMenuItem } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatUtcTime } from '#lib/foundation/time_format';
  import { deleteScreen, type Screen, type ScreenListItem } from '#lib/screen';

  interface Props {
    screens: ScreenListItem[];
    errorMessage: string;
    openScreen: Screen | null;
    openScreenResultId: number | null;
    /** The reason of the last failed "New screen". Empty: no failure. */
    createMessage: string;
    onCreateMessageClose: () => void;
  }

  const { screens, errorMessage, openScreen, openScreenResultId, createMessage, onCreateMessageClose }: Props = $props();

  let deleteTarget = $state<ScreenListItem | null>(null);
  let isDeleting = $state(false);
  let deleteMessage = $state('');

  function screenHref(screenId: number): string {
    return resolve('/screens/[[screenId]]', { screenId: String(screenId) });
  }

  function readMenuItems(key: string): ContextMenuItem[] {
    const screen = screens.find((item) => item.id === Number(key));
    if (screen === undefined) {
      return [];
    }
    return [
      {
        label: 'Open in new tab',
        onSelect: () => {
          window.open(screenHref(screen.id), '_blank', 'noopener');
        },
      },
      {
        label: 'Delete screen',
        divider: true,
        danger: true,
        onSelect: () => {
          deleteTarget = screen;
        },
      },
    ];
  }

  // The list reads again after the change that /ws/screens pushes. Only the open screen leaves the page.
  async function removeScreen(screen: ScreenListItem): Promise<void> {
    isDeleting = true;
    const error = await deleteScreen(fetch, screen.id);
    isDeleting = false;
    deleteTarget = null;
    deleteMessage = error ?? '';
    if (error === null && openScreen?.id === screen.id) {
      await goto(resolve('/screens/[[screenId]]', { screenId: undefined }));
    }
  }

  function runHref(screenId: number, screenResultId: number): string {
    return `${resolve('/screens/[[screenId]]', { screenId: String(screenId) })}?result=${String(screenResultId)}`;
  }
</script>

{#if createMessage !== ''}
  <InlineNotification kind="error" title="Screen not created" subtitle={createMessage} lowContrast onClose={onCreateMessageClose} />
{/if}
{#if deleteMessage !== ''}
  <InlineNotification
    kind="error"
    title="Screen not deleted"
    subtitle={deleteMessage}
    lowContrast
    onClose={() => {
      deleteMessage = '';
    }}
  />
{/if}
{#if deleteTarget !== null}
  {@const target = deleteTarget}
  <Dialog
    open
    onOpenChange={(open: boolean) => {
      if (!open) {
        deleteTarget = null;
      }
    }}
    title="Delete {target.name}"
    primaryText="Delete screen"
    primaryKind="danger"
    busy={isDeleting}
    onPrimary={() => {
      void removeScreen(target);
    }}
  >
    <p>All screen results of the screen are deleted.</p>
  </Dialog>
{/if}
{#if errorMessage !== ''}
  <InlineNotification kind="error" title="Screens not read" subtitle={errorMessage} lowContrast />
{:else}
  <ContextMenu readLabel={(key: string) => screens.find((item) => item.id === Number(key))?.name ?? ''} readItems={readMenuItems}>
    <ScrollRegion label="Screen list" fill>
      <ul class="screen-list">
        {#each screens as screen (screen.id)}
          {@const isOpen = openScreen !== null && openScreen.id === screen.id}
          <li data-context-key={screen.id}>
            <a
              class={['screen-row', isOpen && 'screen-row--open']}
              href={resolve('/screens/[[screenId]]', { screenId: String(screen.id) })}
              aria-current={isOpen ? 'page' : undefined}
            >
              <span class="screen-name">{screen.name}</span>
              <span class="screen-market">{screen.market}</span>
            </a>
            {#if isOpen}
              <ul class="run-list" aria-label="Recent runs">
                {#each openScreen.recent_screen_results as run (run.id)}
                  <li>
                    <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- runHref resolves the path. -->
                    <a class={['run-row', run.id === openScreenResultId && 'run-row--open']} href={runHref(screen.id, run.id)} aria-current={run.id === openScreenResultId ? 'true' : undefined}>
                      <span>{formatUtcTime(run.run_at_utc)}</span>
                      <span class="run-count">{run.result_count}</span>
                    </a>
                  </li>
                {/each}
              </ul>
            {/if}
          </li>
        {/each}
      </ul>
    </ScrollRegion>
  </ContextMenu>
{/if}

<style>
  .screen-list,
  .run-list {
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .screen-row,
  .run-row {
    display: flex;
    gap: var(--cds-spacing-03);
    align-items: center;
    justify-content: space-between;
    min-block-size: var(--cds-spacing-07);
    padding-inline: var(--cds-spacing-05);
    border-block-end: 1px solid var(--cds-border-subtle);
    color: var(--cds-text-primary);
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    text-decoration: none;
  }

  .screen-row:hover,
  .run-row:hover {
    background: var(--cds-layer-hover);
  }

  .screen-row--open,
  .run-row--open {
    background: var(--cds-layer-selected);
  }

  .screen-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .screen-market {
    color: var(--cds-text-secondary);
  }

  .run-row {
    padding-inline-start: var(--cds-spacing-07);
    color: var(--cds-text-secondary);
  }

  .run-count {
    font-variant-numeric: tabular-nums;
  }
</style>
