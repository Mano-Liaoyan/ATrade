<!-- The content of the edit popover of one condition bar tag (docs/architecture/screen.md section 24.10.1, #145
     prototype): the start instruments, the 4 filters, the 3 indicator conditions, and the order. The fields scroll in
     their own ScrollRegion; the buttons stay below them. The parameter ranges come from the indicator catalog
     (GET /api/screen-indicators). The backend checks the values: a 422 problem shows at the tag. -->
<script lang="ts">
  import { Checkbox, Select, TextInput } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import {
    LINE_OUTPUTS,
    MARKET_EXCHANGES,
    START_CHOICES,
    referenceOf,
    type IndicatorConditionKind,
    type ScreenIndicator,
    type ScreenMarket,
  } from './screen_draft';

  type Item = Record<string, unknown>;

  interface Props {
    initial: Item;
    market: ScreenMarket;
    catalog: ScreenIndicator[];
    // A new condition of "Add condition": the primary button adds it, and there is no Remove button.
    isNew: boolean;
    // True for a filter or an indicator condition: the popover has a Remove button.
    canRemove: boolean;
    onApply: (item: Item) => void;
    onRemove: () => void;
    onCancel: () => void;
  }

  const { initial, market, catalog, isNew, canRemove, onApply, onRemove, onCancel }: Props = $props();

  // The popover edits its own copy. The definition changes only on Apply.
  // The page makes a new editor for each tag ({#key}), so the editor reads `initial` only once.
  // svelte-ignore state_referenced_locally
  let item: Item = $state(structuredClone<Item>($state.snapshot(initial)));

  const OPERATORS = [
    { value: '>=', label: '≥' },
    { value: '<=', label: '≤' },
    { value: '>', label: '>' },
    { value: '<', label: '<' },
  ];
  const FILTER_TITLES: Record<string, string> = {
    still_trading: 'Still trading',
    last_price: 'Close',
    average_trading_value_20: 'Avg trading value (20)',
    exchange: 'Exchange',
  };
  const CONDITION_TITLES: Record<string, string> = { compare: 'Indicator', close_versus_line: 'Close vs line', rank: 'Rank' };

  const kind = $derived.by((): string => {
    if ('start' in initial) {
      return 'start';
    }
    if ('direction' in initial) {
      return 'order';
    }
    return typeof initial['field'] === 'string' ? initial['field'] : String(initial['kind']);
  });
  const title = $derived(
    kind === 'start' ? 'Start instruments' : kind === 'order' ? 'Order' : (FILTER_TITLES[kind] ?? CONDITION_TITLES[kind] ?? kind),
  );
  const reference = $derived((item['indicator'] ?? {}) as Item);
  const indicator = $derived(catalog.find((candidate) => candidate.key === reference['indicator']));
  const indicatorItems = $derived(
    (kind === 'close_versus_line' ? catalog.filter((candidate) => candidate.key in LINE_OUTPUTS) : catalog).map(
      (candidate) => ({ value: candidate.key, label: candidate.name }),
    ),
  );

  function text(value: unknown): string {
    return typeof value === 'string' || typeof value === 'number' ? String(value) : '';
  }

  // A number field keeps a text that is not a number, so the backend check names the problem at the tag.
  function readNumber(value: string): number | string {
    const number = Number(value);
    return value.trim() !== '' && Number.isFinite(number) ? number : value;
  }

  function parameterLabel(name: string): string {
    const words = name.replaceAll('_', ' ');
    return words.charAt(0).toUpperCase() + words.slice(1);
  }

  function selectIndicator(key: string): void {
    item['indicator'] = referenceOf(catalog, key, kind === 'order' ? 'order' : (kind as IndicatorConditionKind));
  }

  function setParameter(name: string, value: string): void {
    const parameters = { ...((reference['parameters'] ?? {}) as Item), [name]: readNumber(value) };
    item['indicator'] = { ...reference, parameters };
  }

  function setExchange(exchange: string, checked: boolean): void {
    const values = Array.isArray(item['values']) ? (item['values'] as string[]) : [];
    item['values'] = checked ? [...values, exchange] : values.filter((value) => value !== exchange);
  }

  function setKeepFirst(value: string): void {
    if (value.trim() === '') {
      delete item['keep_first'];
    } else {
      item['keep_first'] = readNumber(value);
    }
  }

  const exchanges = $derived([
    ...MARKET_EXCHANGES[market],
    ...(Array.isArray(initial['values']) ? (initial['values'] as string[]) : []).filter(
      (value) => !MARKET_EXCHANGES[market].includes(value),
    ),
  ]);
</script>

{#snippet comparison()}
  <div class="field-row">
    <Select
      label="Operator"
      items={OPERATORS}
      value={text(item['operator'])}
      onValueChange={(value: string) => {
        item['operator'] = value;
      }}
    />
    <TextInput
      label="Value"
      class="number-input"
      inputmode="decimal"
      value={text(item['value'])}
      oninput={(event: Event) => {
        item['value'] = (event.currentTarget as HTMLInputElement).value;
      }}
    />
  </div>
{/snippet}

{#snippet indicatorFields()}
  <Select
    label={kind === 'close_versus_line' ? 'Line' : 'Indicator'}
    items={indicatorItems}
    value={text(reference['indicator'])}
    onValueChange={selectIndicator}
  />
  {#if indicator !== undefined}
    <div class="field-row">
      {#each indicator.parameters.filter((parameter) => parameter.is_in_name) as parameter (parameter.name)}
        <TextInput
          label={parameterLabel(parameter.name)}
          class="number-input"
          inputmode={parameter.value_type === 'int' ? 'numeric' : 'decimal'}
          value={text(((reference['parameters'] ?? {}) as Item)[parameter.name] ?? parameter.default)}
          oninput={(event: Event) => {
            setParameter(parameter.name, (event.currentTarget as HTMLInputElement).value);
          }}
        />
      {/each}
    </div>
    {#if kind !== 'close_versus_line' && indicator.outputs.length > 1}
      <Select
        label="Output"
        items={indicator.outputs.map((output) => ({ value: output, label: parameterLabel(output) }))}
        value={text(reference['output'])}
        onValueChange={(value: string) => {
          item['indicator'] = { ...reference, output: value };
        }}
      />
    {/if}
  {/if}
{/snippet}

<div class="condition-editor">
  <h2 class="editor-title">{title}</h2>
  <ScrollRegion label={`${title} fields`} maxHeight="20rem">
    <div class="editor-fields">
      {#if kind === 'start'}
        <Select
          label="Instruments"
          items={START_CHOICES[market]}
          value={text(item['start'])}
          onValueChange={(value: string) => {
            item['start'] = value;
          }}
        />
      {:else if kind === 'last_price' || kind === 'average_trading_value_20' || kind === 'compare'}
        {#if kind === 'compare'}
          {@render indicatorFields()}
        {/if}
        {@render comparison()}
      {:else if kind === 'exchange'}
        <fieldset class="cds--fieldset">
          <legend class="cds--visually-hidden">Exchanges</legend>
          {#each exchanges as exchange (exchange)}
            <Checkbox
              label={exchange}
              checked={Array.isArray(item['values']) && (item['values'] as string[]).includes(exchange)}
              onCheckedChange={(checked: boolean) => {
                setExchange(exchange, checked);
              }}
            />
          {/each}
        </fieldset>
      {:else if kind === 'close_versus_line'}
        <Select
          label="Close"
          items={[
            { value: 'above', label: 'above' },
            { value: 'below', label: 'below' },
          ]}
          value={text(item['side'])}
          onValueChange={(value: string) => {
            item['side'] = value;
          }}
        />
        {@render indicatorFields()}
      {:else if kind === 'rank'}
        <div class="field-row">
          <Select
            label="Keep"
            items={[
              { value: 'top', label: 'Top' },
              { value: 'bottom', label: 'Bottom' },
            ]}
            value={text(item['end'])}
            onValueChange={(value: string) => {
              item['end'] = value;
            }}
          />
          <TextInput
            label="%"
            class="number-input"
            inputmode="numeric"
            value={text(item['percent'])}
            oninput={(event: Event) => {
              item['percent'] = readNumber((event.currentTarget as HTMLInputElement).value);
            }}
          />
        </div>
        {@render indicatorFields()}
      {:else if kind === 'order'}
        {@render indicatorFields()}
        <div class="field-row">
          <Select
            label="Direction"
            items={[
              { value: 'descending', label: 'High first' },
              { value: 'ascending', label: 'Low first' },
            ]}
            value={text(item['direction'])}
            onValueChange={(value: string) => {
              item['direction'] = value;
            }}
          />
          <TextInput
            label="First"
            class="number-input"
            inputmode="numeric"
            placeholder="All"
            value={text(item['keep_first'])}
            oninput={(event: Event) => {
              setKeepFirst((event.currentTarget as HTMLInputElement).value);
            }}
          />
        </div>
      {/if}
    </div>
  </ScrollRegion>
  <div class="cds--btn-set editor-actions">
    {#if canRemove && !isNew}
      <button type="button" class="cds--btn cds--btn--ghost cds--btn--danger--ghost" onclick={onRemove}>Remove</button>
    {/if}
    <button type="button" class="cds--btn cds--btn--secondary" onclick={onCancel}>Cancel</button>
    <button
      type="button"
      class="cds--btn cds--btn--primary"
      onclick={() => {
        onApply($state.snapshot<Item>(item));
      }}>{isNew ? 'Add condition' : 'Apply'}</button
    >
  </div>
</div>

<style>
  .editor-title {
    margin: 0;
    padding: var(--cds-spacing-05) var(--cds-spacing-05) var(--cds-spacing-03);
    font-size: var(--cds-heading-compact-01-font-size);
    font-weight: var(--cds-heading-compact-01-font-weight);
    line-height: var(--cds-heading-compact-01-line-height);
    letter-spacing: var(--cds-heading-compact-01-letter-spacing);
  }

  .editor-fields {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-05);
    padding: var(--cds-spacing-03) var(--cds-spacing-05) var(--cds-spacing-05);
  }

  .field-row {
    display: flex;
    gap: var(--cds-spacing-05);
  }

  .field-row > :global(*) {
    flex: 1;
    min-inline-size: 0;
  }

  .cds--fieldset {
    margin: 0;
  }

  /* The buttons share the width of the popover, as in a Carbon modal footer. */
  .editor-actions {
    display: flex;
  }

  .editor-actions .cds--btn {
    flex: 1 1 0;
    min-inline-size: 0;
    max-inline-size: none;
    padding-inline-end: var(--cds-spacing-05);
  }

  /* The number fields: right-aligned with tabular numbers. */
  .condition-editor :global(.number-input) {
    text-align: end;
    font-variant-numeric: tabular-nums;
  }
</style>
