<!-- The text under an equity and drawdown chart (EquityDrawdownChart) of a forward test: the list of the times that the
     grey columns mark. The chart has no curve legend: a page with 2 curves names them with their line styles itself
     (ComparedKeyMetrics). -->
<script lang="ts">
  import { formatUtcTime } from '#lib/foundation/time_format';
  import type { TimeInterval } from './interruption_marks';

  interface Props {
    /** The accessible name of the chart: the list is "<label> interruptions". */
    label: string;
    interruptions: readonly TimeInterval[];
  }

  const { label, interruptions }: Props = $props();
</script>

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
  .interruptions {
    flex: none;
    margin: var(--cds-spacing-03) 0 0;
    padding: 0;
    list-style: none;
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    letter-spacing: var(--cds-body-compact-01-letter-spacing);
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
