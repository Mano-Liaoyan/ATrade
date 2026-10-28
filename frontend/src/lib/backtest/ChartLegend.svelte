<!-- The text under an equity chart (EquityChart, EquityDrawdownChart): with 2 or more curves, a legend with the line
     style of each curve (readCurveStyle); with interruptions, the list of the times that the grey columns mark. -->
<script lang="ts">
  import { LineStyle } from 'lightweight-charts';
  import { formatUtcTime } from '#lib/foundation/time_format';
  import { readCurveStyle } from './chart_series';
  import type { TimeInterval } from './interruption_marks';

  interface Props {
    /** The accessible name of the chart: the lists are "<label> legend" and "<label> interruptions". */
    label: string;
    curveNames: readonly string[];
    interruptions: readonly TimeInterval[];
  }

  const { label, curveNames, interruptions }: Props = $props();
</script>

{#if curveNames.length > 1}
  <ul class="legend" aria-label={`${label} legend`}>
    {#each curveNames as curveName, curveIndex (curveIndex)}
      <li>
        <span
          class="legend-line"
          class:dashed={readCurveStyle(curveIndex).lineStyle === LineStyle.Dashed}
          style:border-color={`var(${readCurveStyle(curveIndex).colorVariable})`}
        ></span>
        {curveName}
      </li>
    {/each}
  </ul>
{/if}
{#if interruptions.length > 0}
  <ul class="interruptions" aria-label={`${label} interruptions`}>
    {#each interruptions as interruption (interruption.start_utc)}
      <li>
        <span class="interruption-mark"></span>
        Interrupted from {formatUtcTime(interruption.start_utc)} to {formatUtcTime(interruption.end_utc)}
      </li>
    {/each}
  </ul>
{/if}

<style>
  .legend,
  .interruptions {
    flex: none;
    margin: var(--cds-spacing-03) 0 0;
    padding: 0;
    list-style: none;
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    letter-spacing: var(--cds-body-compact-01-letter-spacing);
  }

  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: var(--cds-spacing-05);
  }

  .legend li {
    display: flex;
    align-items: center;
    gap: var(--cds-spacing-03);
  }

  .legend-line {
    display: inline-block;
    inline-size: var(--cds-spacing-07);
    border-top: 2px solid;
  }

  .legend-line.dashed {
    border-top-style: dashed;
  }

  .interruption-mark {
    display: inline-block;
    inline-size: var(--cds-spacing-04);
    block-size: var(--cds-spacing-04);
    margin-inline-end: var(--cds-spacing-03);
    background: var(--cds-layer-accent-01);
    vertical-align: middle;
  }
</style>
