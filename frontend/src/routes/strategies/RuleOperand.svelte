<!-- One side of a rule condition: a price, an indicator with its parameters (and its line for a multi-line
     indicator), or a number (right side only). -->
<script lang="ts">
  import { Button, Select } from '#lib/foundation/carbon';
  import {
    createOperand,
    findIndicatorChoice,
    listOperandChoices,
    readCurrentOperand,
    readOperandChoice,
    type OperandChoice,
    type RightOperand,
  } from '#lib/strategy';
  import RuleNumberInput from './RuleNumberInput.svelte';
  import { readIndicatorCatalog } from './indicator_catalog_context';

  interface Props {
    label: string;
    side: 'left' | 'right' | 'rank';
    operand: RightOperand;
    onOperandChange: (operand: RightOperand) => void;
  }

  const { label, side, operand, onOperandChange }: Props = $props();

  const catalog = readIndicatorCatalog();
  const choices = $derived(listOperandChoices(side, catalog(), operand));
  const indicator = $derived(operand.type === 'indicator' ? findIndicatorChoice(operand.indicator, catalog()) : undefined);
  const currentOperand = $derived(readCurrentOperand(operand, catalog()));
</script>

<span class="rule-operand">
  <span class="rule-operand__select">
    <Select
      {label}
      hideLabel
      size="sm"
      items={choices}
      value={readOperandChoice(operand)}
      onValueChange={(choice: OperandChoice) => {
        onOperandChange(createOperand(choice, catalog()));
      }}
    />
  </span>
  {#if currentOperand !== null}
    {@const newOperand = currentOperand}
    <Button
      kind="ghost"
      size="sm"
      aria-label="Use current expression in {label}"
      onclick={() => {
        onOperandChange(newOperand);
      }}
    >
      Use current expression
    </Button>
  {/if}
  {#if operand.type === 'indicator' && indicator !== undefined}
    {@const indicatorOperand = operand}
    <span class="rule-operand__paren" aria-hidden="true">(</span>
    {#each indicator.parameters as parameter, index (parameter.name)}
      {#if index > 0}<span class="rule-operand__paren" aria-hidden="true">,</span>{/if}
      <RuleNumberInput
        label="{label} {indicator.label} {parameter.name}"
        value={indicatorOperand.parameters?.[parameter.name] ?? parameter.default}
        isInteger={parameter.isInteger}
        minimum={parameter.minimum}
        maximum={parameter.maximum}
        onValueChange={(value: number) => {
          onOperandChange({ ...indicatorOperand, parameters: { ...indicatorOperand.parameters, [parameter.name]: value } });
        }}
      />
    {/each}
    <span class="rule-operand__paren" aria-hidden="true">)</span>
    {#if indicator.lines.length > 0}
      <span class="rule-operand__select">
        <Select
          label="{label} line"
          hideLabel
          size="sm"
          items={indicator.lines.map(([value, lineLabel]) => ({ value, label: lineLabel }))}
          value={indicatorOperand.output ?? indicator.lines[0]?.[0] ?? ''}
          onValueChange={(output: string) => {
            onOperandChange({ ...indicatorOperand, output });
          }}
        />
      </span>
    {/if}
  {:else if operand.type === 'number'}
    {@const numberOperand = operand}
    <RuleNumberInput
      label="{label} number"
      value={numberOperand.value}
      isInteger={false}
      onValueChange={(value: number) => {
        onOperandChange({ ...numberOperand, value });
      }}
    />
  {/if}
</span>

<style>
  .rule-operand {
    display: inline-flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--cds-spacing-02);
  }

  .rule-operand__select {
    inline-size: var(--cds-spacing-13);
  }

  .rule-operand__paren {
    color: var(--cds-text-helper);
  }
</style>
