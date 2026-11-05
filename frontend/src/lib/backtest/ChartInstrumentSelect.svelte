<!-- The "Instrument" select of the "Bars" view of a multi-instrument backtest (docs/architecture/indicator.md section
     23.9.8): a Carbon sm dropdown with the height of ChartViewSwitcher. -->
<script lang="ts">
  import { Select } from '#lib/foundation/carbon';
  import type { BacktestInstrument } from './backtest_api';

  interface Props {
    instruments: BacktestInstrument[];
    value: BacktestInstrument;
    onValueChange: (value: BacktestInstrument) => void;
  }

  const { instruments, value, onValueChange }: Props = $props();

  function toItemValue({ symbol, exchange }: BacktestInstrument): string {
    return `${symbol}:${exchange}`;
  }

  const items = $derived(instruments.map((instrument) => ({ value: toItemValue(instrument), label: instrument.symbol })));
</script>

<div class="chart-instrument">
  <Select
    label="Instrument"
    hideLabel
    size="sm"
    {items}
    value={toItemValue(value)}
    onValueChange={(selected: string) => {
      const instrument = instruments.find((item) => toItemValue(item) === selected);
      if (instrument !== undefined) {
        onValueChange(instrument);
      }
    }}
  />
</div>

<style>
  /* A compact select in the 32px header line: 24px high, like ChartViewSwitcher. */
  .chart-instrument {
    flex: none;
    inline-size: calc(var(--cds-spacing-09) * 2);
  }

  .chart-instrument :global(.cds--list-box),
  .chart-instrument :global(.cds--list-box__field) {
    block-size: var(--cds-spacing-06);
    max-block-size: var(--cds-spacing-06);
  }

  /* The padding and the type of ChartViewSwitcher, so that a symbol fits. */
  .chart-instrument :global(.cds--list-box__field) {
    padding-inline: var(--cds-spacing-03) var(--cds-spacing-07);
    font-size: var(--cds-label-01-font-size);
    line-height: var(--cds-label-01-line-height);
    letter-spacing: var(--cds-label-01-letter-spacing);
  }

  .chart-instrument :global(.cds--list-box__menu-icon) {
    inset-inline-end: var(--cds-spacing-03);
  }
</style>
