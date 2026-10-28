<!-- One metric as a Carbon tile in a MetricRow: the name and the value. With `change`, the value is a ChangeText: its
     sign gives the direction, shown with an arrow icon and the Carbon support color, so the color is never the only
     sign (AGENTS.md, State). The value is right-aligned with tabular numbers. A value that does not fit ends with an
     ellipsis, and its title gives the full value. -->
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
  <dt title={name}>{name}</dt>
  <dd title={text}>
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

  /* A narrow tile clips the value with an ellipsis; the title gives the full value. */
  dd {
    overflow: hidden;
    text-align: end;
    text-overflow: ellipsis;
    margin: var(--cds-spacing-02) 0 0;
    font-size: var(--cds-heading-compact-02-font-size);
    font-weight: var(--cds-heading-compact-02-font-weight);
    line-height: var(--cds-heading-compact-02-line-height);
    letter-spacing: var(--cds-heading-compact-02-letter-spacing);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
</style>
