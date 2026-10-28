<!-- One metric as a Carbon tile in a MetricRow: the name and the value. With `change`, the value is a ChangeText: its
     sign gives the direction, shown with an arrow icon and the Carbon support color, so the color is never the only
     sign (AGENTS.md, State). The value is right-aligned with tabular numbers. -->
<script lang="ts">
  import { ChangeText } from '#lib/foundation/value_format';

  interface Props {
    name: string;
    /** The value as text, for example from formatSignedNumber. */
    text: string;
    /** The value as a number when it is an up or down change. Null is a missing change. */
    change?: number | null;
  }

  const { name, text, change }: Props = $props();
</script>

<div class="cds--tile metric-tile">
  <dt>{name}</dt>
  <dd>
    {#if change === undefined}
      {text}
    {:else}
      <ChangeText value={change} {text} />
    {/if}
  </dd>
</div>

<style>
  .metric-tile {
    min-block-size: 0;
    min-inline-size: 0;
    padding: var(--cds-spacing-03) var(--cds-spacing-05);
  }

  dt {
    overflow: hidden;
    font-size: var(--cds-label-01-font-size);
    line-height: var(--cds-label-01-line-height);
    letter-spacing: var(--cds-label-01-letter-spacing);
    color: var(--cds-text-secondary);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  dd {
    display: flex;
    justify-content: flex-end;
    margin: var(--cds-spacing-02) 0 0;
    font-size: var(--cds-heading-compact-02-font-size);
    font-weight: var(--cds-heading-compact-02-font-weight);
    line-height: var(--cds-heading-compact-02-line-height);
    letter-spacing: var(--cds-heading-compact-02-letter-spacing);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
</style>
