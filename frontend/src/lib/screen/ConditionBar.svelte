<!-- The read-only condition bar (docs/architecture/screen.md section 24.10.1): 4 group strips in a fixed order with a
     chevron between 2 groups. Each condition is a Carbon tag with 3 text parts (subject, operation, value). Each group
     ends with its funnel count; the count of the last group is bold. The screen page and the condition card of the AI
     assistant use it. -->
<script lang="ts">
  import ChevronRight16 from '@carbon/icons/es/chevron--right/16.js';
  import { Icon } from '#lib/foundation/carbon';
  import { buildConditionGroups, type FunnelCounts, type IndicatorNames, type ScreenDefinition } from './condition_bar';

  interface Props {
    definition: ScreenDefinition;
    indicatorNames: IndicatorNames;
    counts: FunnelCounts;
  }

  const { definition, indicatorNames, counts }: Props = $props();

  const groups = $derived(buildConditionGroups(definition, indicatorNames, counts));
  const COUNT_FORMAT = new Intl.NumberFormat('en-US');
</script>

<ul class="condition-bar" aria-label="Conditions">
  {#each groups as group, index (group.label)}
    {#if index > 0}
      <li class="chevron" aria-hidden="true"><Icon icon={ChevronRight16} /></li>
    {/if}
    <li class="group" aria-label={group.label}>
      {#each group.tags as tag, tagIndex (tagIndex)}
        <span class="cds--tag cds--tag--gray condition-tag">
          <span class="cds--tag__label">
            <span class="subject">{tag.subject}</span>
            {#if tag.operation !== ''}<span class="operation">{tag.operation}</span>{/if}
            {#if tag.value !== ''}<span class="value">{tag.value}</span>{/if}
          </span>
        </span>
      {/each}
      <span class={['count', index === groups.length - 1 && 'count-last']} aria-label={`${group.label} count`}
        >{COUNT_FORMAT.format(group.count)}</span
      >
    </li>
  {/each}
</ul>

<style>
  .condition-bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--cds-spacing-03);
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .chevron {
    display: flex;
    color: var(--cds-icon-secondary);
  }

  .group {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--cds-spacing-02);
    padding: var(--cds-spacing-02) var(--cds-spacing-03);
    border-radius: var(--cds-spacing-03);
    background: var(--cds-background);
  }

  .condition-tag {
    margin: 0;
  }

  .condition-tag .cds--tag__label {
    display: inline-flex;
    gap: var(--cds-spacing-02);
  }

  .subject {
    color: var(--cds-text-primary);
  }

  .operation {
    color: var(--cds-text-helper);
  }

  /* The value color: $link-primary (blue 60 in g10, blue 40 in g100), section 24.13. */
  .value {
    color: var(--cds-link-primary);
  }

  .count {
    margin-inline-start: var(--cds-spacing-02);
    font-size: var(--cds-body-compact-01-font-size);
    font-variant-numeric: tabular-nums;
    color: var(--cds-text-secondary);
  }

  .count-last {
    font-weight: 600;
    color: var(--cds-text-primary);
  }
</style>
