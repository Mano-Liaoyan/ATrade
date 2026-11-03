<!-- The legend of one chart pane (docs/architecture/indicator.md section 23.9.4): an HTML layer at the top left of the
     pane, over the canvas. The price pane has the OHLC row first. Each indicator has one row: its legend name and one
     value for each line, in the line color. IBM Plex Mono with tabular numbers, Carbon label-01. -->
<script lang="ts">
  import type { LegendBar, LegendRow } from './chart_indicators';

  interface Props {
    /** The OHLC row of the price pane. Null for an own pane, or before the bars load. */
    bar?: LegendBar | null;
    rows: LegendRow[];
  }

  const { bar = null, rows }: Props = $props();
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
      <li class="legend-row">
        <span class="legend-name">{row.name}</span>
        {#each row.values as value, valueIndex (valueIndex)}
          <span class="legend-value" style:color={value.color}>{value.text}</span>
        {/each}
      </li>
    {/each}
  </ul>
{/if}

<style>
  /* The legend does not take pointer events, so the crosshair follows the pointer also over the legend. */
  .chart-legend {
    position: absolute;
    inset-block-start: var(--cds-spacing-02);
    inset-inline-start: var(--cds-spacing-03);
    z-index: 1;
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
    gap: var(--cds-spacing-03);
    white-space: nowrap;
  }

  .legend-letter,
  .legend-name {
    color: var(--cds-text-secondary);
  }

  .legend-number {
    margin-inline-end: var(--cds-spacing-02);
    color: var(--cds-text-primary);
  }
</style>
