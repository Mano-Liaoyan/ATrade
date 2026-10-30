<!-- A group of the rule builder: "All of" or "Any of", its conditions, and (only in the top group) groups of
     conditions (docs/architecture/strategy.md section 9.8.2). -->
<script lang="ts">
  import Add16 from '@carbon/icons/es/add/16.js';
  import Close16 from '@carbon/icons/es/close/16.js';
  import { Button, ContentSwitcher, Icon, IconButton, Select } from '#lib/foundation/carbon';
  import {
    COMPARISON_CHOICES,
    createCondition,
    createGroup,
    type Comparison,
    type GroupMatch,
    type InnerRuleGroup,
    type LeftOperand,
    type RuleCondition,
    type RightOperand,
    type RuleGroup,
  } from '#lib/strategy';
  import RuleGroupEditor from './RuleGroupEditor.svelte';
  import RuleOperand from './RuleOperand.svelte';

  type Group = RuleGroup | InnerRuleGroup;
  type Item = RuleGroup['items'][number];

  interface Props {
    /** The accessible name of the group, for example "Entry" or "Entry group 2". */
    label: string;
    group: Group;
    isNested?: boolean;
    onGroupChange: (group: Group) => void;
    onRemove?: () => void;
  }

  const { label, group, isNested = false, onGroupChange, onRemove }: Props = $props();

  const MATCH_ITEMS: { value: GroupMatch; label: string }[] = [
    { value: 'all_of', label: 'All of' },
    { value: 'any_of', label: 'Any of' },
  ];

  function changeItems(items: Item[]): void {
    onGroupChange({ ...group, items });
  }

  function replaceItem(index: number, item: Item): void {
    changeItems(group.items.map((current, currentIndex) => (currentIndex === index ? item : current)));
  }

  function removeItem(index: number): void {
    changeItems(group.items.filter((_item, currentIndex) => currentIndex !== index));
  }

  function changeCondition(index: number, condition: RuleCondition, change: Partial<RuleCondition>): void {
    replaceItem(index, { ...condition, ...change });
  }
</script>

<div class={['rule-group', isNested && 'rule-group--nested']} role="group" aria-label={label}>
  <div class="rule-group__head">
    <span class="rule-group__match">
      <ContentSwitcher
        label="{label} match"
        size="sm"
        items={MATCH_ITEMS}
        value={group.match}
        onValueChange={(match: GroupMatch) => {
          onGroupChange({ ...group, match });
        }}
      />
    </span>
    {#if onRemove !== undefined}
      <IconButton label="Remove group" icon={Close16} tone="neutral" onclick={onRemove} />
    {/if}
  </div>
  {#each group.items as item, index (index)}
    {@const itemLabel = `${label} ${item.type === 'group' ? 'group' : 'condition'} ${String(index + 1)}`}
    <div class="rule-group__row">
      <span class="rule-group__join">{index === 0 ? '' : group.match === 'all_of' ? 'and' : 'or'}</span>
      {#if item.type === 'group'}
        <div class="rule-group__nested">
          <RuleGroupEditor
            label={itemLabel}
            group={item}
            isNested
            onGroupChange={(changed: Group) => {
              replaceItem(index, changed as InnerRuleGroup);
            }}
            onRemove={() => {
              removeItem(index);
            }}
          />
        </div>
      {:else}
        <RuleOperand
          label="{itemLabel} left side"
          side="left"
          operand={item.left}
          onOperandChange={(left: RightOperand) => {
            changeCondition(index, item, { left: left as LeftOperand });
          }}
        />
        <span class="rule-group__comparison">
          <Select
            label="{itemLabel} comparison"
            hideLabel
            size="sm"
            items={COMPARISON_CHOICES}
            value={item.comparison}
            onValueChange={(comparison: Comparison) => {
              changeCondition(index, item, { comparison });
            }}
          />
        </span>
        <RuleOperand
          label="{itemLabel} right side"
          side="right"
          operand={item.right}
          onOperandChange={(right: RightOperand) => {
            changeCondition(index, item, { right });
          }}
        />
        <IconButton
          label="Remove condition"
          icon={Close16}
          tone="neutral"
          onclick={() => {
            removeItem(index);
          }}
        />
      {/if}
    </div>
  {/each}
  <div class="rule-group__row">
    <span class="rule-group__join"></span>
    <Button
      kind="ghost"
      size="sm"
      aria-label="Add condition to {label}"
      onclick={() => {
        changeItems([...group.items, createCondition()]);
      }}
    >
      Add condition<Icon icon={Add16} class="cds--btn__icon" />
    </Button>
    {#if !isNested}
      <Button
        kind="ghost"
        size="sm"
        aria-label="Add group to {label}"
        onclick={() => {
          changeItems([...group.items, createGroup()]);
        }}
      >
        Add group<Icon icon={Add16} class="cds--btn__icon" />
      </Button>
    {/if}
  </div>
</div>

<style>
  .rule-group {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-03);
    padding-inline-start: var(--cds-spacing-04);
    border-inline-start: 2px solid var(--cds-border-subtle-01);
  }

  .rule-group--nested {
    padding-block: var(--cds-spacing-03);
    border-inline-start-color: var(--cds-border-strong-01);
  }

  .rule-group__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--cds-spacing-03);
  }

  .rule-group__match {
    inline-size: var(--cds-spacing-13);
  }

  .rule-group__row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--cds-spacing-02);
  }

  .rule-group__join {
    flex: none;
    inline-size: var(--cds-spacing-07);
    color: var(--cds-text-helper);
    text-align: end;
    font-size: var(--cds-label-01-font-size, 0.75rem);
  }

  .rule-group__nested {
    flex: 1;
    min-inline-size: 0;
  }

  .rule-group__comparison {
    inline-size: var(--cds-spacing-13);
  }
</style>
