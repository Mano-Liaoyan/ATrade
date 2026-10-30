<!-- The screen list of the screen workbench (the body of the "Screens" side column): each row has the name and the
     market. The open screen expands to its recent runs (time and instrument count). A click on a run opens its screen
     result (docs/architecture/screen.md section 24.10). -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { InlineNotification } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatUtcTime } from '#lib/foundation/time_format';
  import type { Screen, ScreenListItem } from '#lib/screen';

  interface Props {
    screens: ScreenListItem[];
    errorMessage: string;
    openScreen: Screen | null;
    openScreenResultId: number | null;
  }

  const { screens, errorMessage, openScreen, openScreenResultId }: Props = $props();

  function runHref(screenId: number, screenResultId: number): string {
    return `${resolve('/screens/[[screenId]]', { screenId: String(screenId) })}?result=${String(screenResultId)}`;
  }
</script>

{#if errorMessage !== ''}
  <InlineNotification kind="error" title="Screens not read" subtitle={errorMessage} lowContrast />
{:else}
  <ScrollRegion label="Screen list" fill>
    <ul class="screen-list">
      {#each screens as screen (screen.id)}
        {@const isOpen = openScreen !== null && openScreen.id === screen.id}
        <li>
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
