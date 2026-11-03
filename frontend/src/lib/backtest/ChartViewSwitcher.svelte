<!-- The "Equity" / "Bars" switcher of the backtest and forward test panel header lines (docs/architecture/indicator.md
     section 23.9.8): a Carbon sm content switcher of the size of the bar period switcher of the instrument page. -->
<script lang="ts">
  import { ContentSwitcher } from '#lib/foundation/carbon';
  import { CHART_VIEW_ITEMS, type ChartView } from './chart_view';

  interface Props {
    value: ChartView;
    onValueChange: (value: ChartView) => void;
  }

  const { value, onValueChange }: Props = $props();
</script>

<div class="chart-views">
  <ContentSwitcher label="Chart" size="sm" items={[...CHART_VIEW_ITEMS]} {value} {onValueChange} />
</div>

<style>
  /* A compact switcher in the 32px header line: 24px high, centered, so it does not touch the borders of the line. */
  .chart-views {
    display: flex;
    flex: none;
    align-items: center;
  }

  .chart-views :global(.cds--content-switcher) {
    block-size: var(--cds-spacing-06);
    inline-size: calc(var(--cds-spacing-09) * 3);
  }

  .chart-views :global(.cds--content-switcher-btn) {
    justify-content: center;
    padding-inline: var(--cds-spacing-03);
    font-size: var(--cds-label-01-font-size);
    line-height: var(--cds-label-01-line-height);
    letter-spacing: var(--cds-label-01-letter-spacing);
  }
</style>
