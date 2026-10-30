<!-- The condition bar (docs/architecture/screen.md section 24.10.1): 4 group strips in a fixed order with a chevron
     between 2 groups. Each condition is a Carbon tag with 3 text parts (subject, operation, value). Each group ends
     with its funnel count; the count of the last group is bold. Without `onEdit` the bar is read-only (the condition
     card of the AI assistant). With it, a click on a tag opens its edit popover, the × button of a filter or an
     indicator condition removes it, and the indicator conditions end with the "Add condition" menu. A tag with a
     problem of a 422 answer shows the error icon and the problem next to it. -->
<script lang="ts">
  import ChevronRight16 from '@carbon/icons/es/chevron--right/16.js';
  import Close16 from '@carbon/icons/es/close/16.js';
  import WarningFilled16 from '@carbon/icons/es/warning--filled/16.js';
  import { Icon, MenuButton, type MenuButtonItem } from '#lib/foundation/carbon';
  import { buildConditionGroups, type FunnelCounts, type IndicatorNames, type ScreenDefinition } from './condition_bar';
  import { targetKey, type ConditionKind, type ConditionTarget } from './screen_draft';

  type ListTarget = ConditionTarget & { part: 'filters' | 'indicator_conditions' };

  interface Props {
    definition: ScreenDefinition;
    indicatorNames: IndicatorNames;
    counts: FunnelCounts | null;
    // The problems of a 422 answer by targetKey.
    problems?: Map<string, string[]>;
    onEdit?: (target: ConditionTarget, anchor: HTMLElement) => void;
    onRemove?: (target: ListTarget) => void;
    onAdd?: (kind: ConditionKind, anchor: HTMLElement | null) => void;
  }

  const { definition, indicatorNames, counts, problems = new Map(), onEdit, onRemove, onAdd }: Props = $props();

  const groups = $derived(buildConditionGroups(definition, indicatorNames, counts));
  const COUNT_FORMAT = new Intl.NumberFormat('en-US');

  // The definition part of each group, in the order of the groups.
  const GROUP_PARTS = ['start', 'filters', 'indicator_conditions', 'order'] as const;

  function targetOf(groupIndex: number, tagIndex: number): ConditionTarget {
    const part = GROUP_PARTS[groupIndex] ?? 'order';
    return part === 'start' || part === 'order' ? { part } : { part, index: tagIndex };
  }

  function listTargetOf(target: ConditionTarget): ListTarget | null {
    return target.part === 'filters' || target.part === 'indicator_conditions' ? target : null;
  }

  const ADD_ITEMS: [ConditionKind, string][] = [
    ['last_price', 'Close'],
    ['average_trading_value_20', 'Avg trading value (20)'],
    ['exchange', 'Exchange'],
    ['still_trading', 'Still trading'],
    ['compare', 'Indicator'],
    ['close_versus_line', 'Close vs line'],
    ['rank', 'Rank'],
  ];
  const addItems: MenuButtonItem[] = $derived(
    ADD_ITEMS.map(([kind, label]) => ({
      label,
      divider: kind === 'compare',
      onSelect: (anchor: HTMLElement | null) => onAdd?.(kind, anchor),
    })),
  );
</script>

<ul class="condition-bar" aria-label="Conditions">
  {#each groups as group, index (group.label)}
    {#if index > 0}
      <li class="chevron" aria-hidden="true"><Icon icon={ChevronRight16} /></li>
    {/if}
    <li class="group" aria-label={group.label}>
      {#each group.tags as tag, tagIndex (tagIndex)}
        {@const target = targetOf(index, tagIndex)}
        {@const tagProblems = problems.get(targetKey(target)) ?? []}
        {@const listTarget = onRemove === undefined ? null : listTargetOf(target)}
        {@const tagText = `${tag.subject} ${tag.operation} ${tag.value}`.replace(/\s+/g, ' ').trim()}
        <span class={['cds--tag cds--tag--gray condition-tag', listTarget !== null && 'cds--tag--filter', tagProblems.length > 0 && 'tag-invalid']}>
          {#if tagProblems.length > 0}
            <Icon icon={WarningFilled16} class="problem-icon" />
          {/if}
          {#if onEdit !== undefined}
            <button
              type="button"
              class="cds--tag__label tag-edit"
              aria-label={`Edit ${tagText}`}
              onclick={(event) => {
                onEdit(target, event.currentTarget);
              }}
            >
              <span class="subject">{tag.subject}</span>
              {#if tag.operation !== ''}<span class="operation">{tag.operation}</span>{/if}
              {#if tag.value !== ''}<span class="value">{tag.value}</span>{/if}
            </button>
          {:else}
            <span class="cds--tag__label">
              <span class="subject">{tag.subject}</span>
              {#if tag.operation !== ''}<span class="operation">{tag.operation}</span>{/if}
              {#if tag.value !== ''}<span class="value">{tag.value}</span>{/if}
            </span>
          {/if}
          {#if listTarget !== null}
            <button
              type="button"
              class="cds--tag__close-icon"
              aria-label={`Remove ${tagText}`}
              onclick={() => {
                onRemove?.(listTarget);
              }}><Icon icon={Close16} /></button
            >
          {/if}
        </span>
        {#each tagProblems as problem, problemIndex (problemIndex)}
          <span class="problem-text" role="alert">{problem}</span>
        {/each}
      {/each}
      {#if onAdd !== undefined && GROUP_PARTS[index] === 'indicator_conditions'}
        <MenuButton label="Add condition" items={addItems} />
      {/if}
      {#if group.count !== null}
        <span class={['count', index === groups.length - 1 && 'count-last']} aria-label={`${group.label} count`}
          >{COUNT_FORMAT.format(group.count)}</span
        >
      {/if}
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

  /* A tag shows its full text: the value is the data that the user reads. */
  .condition-tag .cds--tag__label {
    max-inline-size: none;
    display: inline-flex;
    gap: var(--cds-spacing-02);
  }

  .tag-edit {
    padding: 0;
    border: 0;
    background: none;
    font: inherit;
    cursor: pointer;
  }

  /* A tag with a problem: the error icon and an error outline, as a Carbon invalid field. */
  .tag-invalid {
    outline: 1px solid var(--cds-support-error);
    outline-offset: -1px;
  }

  .condition-tag :global(.problem-icon) {
    margin-inline-end: var(--cds-spacing-02);
    fill: var(--cds-support-error);
  }

  /* The problem text of a Carbon invalid field ($helper-text-01, $text-error). */
  .problem-text {
    font-size: var(--cds-helper-text-01-font-size);
    line-height: var(--cds-helper-text-01-line-height);
    letter-spacing: var(--cds-helper-text-01-letter-spacing);
    color: var(--cds-text-error);
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
    font-weight: var(--cds-heading-compact-01-font-weight);
    color: var(--cds-text-primary);
  }
</style>
