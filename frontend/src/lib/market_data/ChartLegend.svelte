<!-- The legend of one chart pane (docs/architecture/indicator.md section 23.9.4). ChartPaneOverlay puts it at the top
     left of the pane, over the canvas. The price pane has the OHLC row first. Each indicator has one row: its legend name and one
     value for each line, in the line color. IBM Plex Mono with tabular numbers, Carbon label-01.
     With `actions`, a row shows 3 ghost icon buttons when the pointer is on it or the focus is in it: Hide or Show,
     Settings, and Remove. A hidden indicator keeps its row with a disabled name, no values, and the Show button always
     shown. A click on the name also opens the settings. -->
<script lang="ts">
  import Close16 from '@carbon/icons/es/close/16.js';
  import Settings16 from '@carbon/icons/es/settings/16.js';
  import View16 from '@carbon/icons/es/view/16.js';
  import ViewOff16 from '@carbon/icons/es/view--off/16.js';
  import { IconButton } from '#lib/foundation/carbon';
  import type { LegendBar, LegendRow, LegendRowActions } from './chart_indicators';

  interface Props {
    /** The OHLC row of the price pane. Null for an own pane, or before the bars load. */
    bar?: LegendBar | null;
    rows: LegendRow[];
    /** The row buttons. Without them the rows have no buttons. */
    actions?: LegendRowActions;
  }

  const { bar = null, rows, actions }: Props = $props();

  const rowElements: HTMLLIElement[] = $state([]);
</script>

{#if bar !== null || rows.length > 0}
  <ul class="chart-legend" aria-label="Legend">
    {#if bar !== null}
      <li class="legend-row">
        <span class="legend-letter">O</span>
        <span class="legend-number">{bar.open}</span>
        <span class="legend-letter">H</span>
        <span class="legend-number">{bar.high}</span>
        <span class="legend-letter">L</span>
        <span class="legend-number">{bar.low}</span>
        <span class="legend-letter">C</span>
        <span class="legend-number">{bar.close}</span>
      </li>
    {/if}
    {#each rows as row, index (index)}
      <li class={['legend-row', actions !== undefined && 'legend-row--actions', row.hidden && 'legend-row--hidden']} bind:this={rowElements[index]}>
        {#if actions === undefined}
          <span class="legend-name">{row.name}</span>
        {:else}
          <!-- The Settings button gives the same action to the keyboard, so the name is not in the tab order. -->
          <button
            type="button"
            class="legend-name legend-name-button"
            tabindex="-1"
            onclick={() => {
              const anchor = rowElements[index];
              if (anchor !== undefined) {
                actions.onOpenSettings(row, anchor);
              }
            }}>{row.name}</button
          >
        {/if}
        {#each row.values as value, valueIndex (valueIndex)}
          <span class="legend-value" style:color={value.color}>{value.text}</span>
        {/each}
        {#if actions !== undefined}
          <span class="legend-actions">
            <span class={['legend-action', row.hidden && 'legend-action--shown']}>
              <IconButton
                label={row.hidden ? `Show ${row.name}` : `Hide ${row.name}`}
                icon={row.hidden ? ViewOff16 : View16}
                size="xs"
                floatingTooltip
                onclick={() => {
                  actions.onToggleHidden(row);
                }}
              />
            </span>
            <span class="legend-action">
              <IconButton
                label={`Settings for ${row.name}`}
                icon={Settings16}
                size="xs"
                floatingTooltip
                onclick={() => {
                  const anchor = rowElements[index];
                  if (anchor !== undefined) {
                    actions.onOpenSettings(row, anchor);
                  }
                }}
              />
            </span>
            <span class="legend-action">
              <IconButton
                label={`Remove ${row.name}`}
                icon={Close16}
                size="xs"
                floatingTooltip
                onclick={() => {
                  actions.onRemove(row);
                }}
              />
            </span>
          </span>
        {/if}
      </li>
    {/each}
  </ul>
{/if}

<style>
  /* The legend does not take pointer events, so the crosshair follows the pointer also over the legend. In a row with
     buttons, the name, the values, and a shown button take them, so a trade mark under a hidden button stays reachable.
     The row with the pointer or the focus takes them all. */
  .chart-legend {
    margin: 0;
    padding: 0;
    list-style: none;
    pointer-events: none;
    font-family: var(--cds-code-01-font-family, 'IBM Plex Mono', monospace);
    font-size: var(--cds-label-01-font-size);
    line-height: var(--cds-label-01-line-height);
    letter-spacing: var(--cds-label-01-letter-spacing);
    font-variant-numeric: tabular-nums;
  }

  .legend-row {
    display: flex;
    align-items: center;
    gap: var(--cds-spacing-03);
    white-space: nowrap;
  }

  .legend-row--actions .legend-name,
  .legend-row--actions .legend-value,
  .legend-row--actions .legend-action--shown,
  .legend-row--actions:hover,
  .legend-row--actions:focus-within {
    pointer-events: auto;
  }

  .legend-letter,
  .legend-name {
    color: var(--cds-text-secondary);
  }

  .legend-row--hidden .legend-name {
    color: var(--cds-text-disabled);
  }

  .legend-name-button {
    padding: 0;
    border: 0;
    background: none;
    font: inherit;
    letter-spacing: inherit;
    cursor: pointer;
  }

  .legend-name-button:hover {
    color: var(--cds-text-primary);
    text-decoration: underline;
  }

  .legend-number {
    margin-inline-end: var(--cds-spacing-02);
    color: var(--cds-text-primary);
  }

  .legend-actions {
    display: flex;
  }

  /* The buttons show when the pointer is on the row or the focus is in it. They stay in the tab order. */
  .legend-action {
    opacity: 0;
  }

  .legend-row:hover .legend-action,
  .legend-row:focus-within .legend-action,
  .legend-action--shown {
    opacity: 1;
  }
</style>
