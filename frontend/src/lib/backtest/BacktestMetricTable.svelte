<!-- The Metrics table of a backtest (docs/architecture/backtest.md section 10.9.6): a Carbon data table with 32px rows,
     the columns Metric and All, and right-aligned tabular numbers. Each metric name is a Carbon definition term with a
     tooltip: its definition and "Risk-free rate: 0". A "–" value with a reason of the API has a tooltip with the
     reason. The table fills the height of its panel body and scrolls in its own ScrollRegion. -->
<script lang="ts">
  import { DataTable, Tooltip, type TableColumn } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import type { BacktestMetrics } from './backtest_api';
  import { readMetricRows } from './metric_table';

  const { metrics }: { metrics: BacktestMetrics } = $props();

  const COLUMNS: TableColumn[] = [{ header: 'Metric' }, { header: 'All', align: 'right' }];

  const metricRows = $derived(readMetricRows([metrics]));
</script>

<ScrollRegion label="Metrics" fill>
  <DataTable columns={COLUMNS} size="sm">
    {#snippet rows()}
      {#each metricRows as row (row.name)}
        <tr>
          <th scope="row">
            <Tooltip text={row.definition} align="right">
              {#snippet trigger({ props })}
                <button {...props} type="button" class="cds--definition-term">{row.name}</button>
              {/snippet}
            </Tooltip>
          </th>
          {#each row.values as value, valueIndex (valueIndex)}
            <td align="right">
              {#if value.reason === undefined}
                {value.text}
              {:else}
                <Tooltip text={value.reason} align="left">
                  {#snippet trigger({ props })}
                    <button {...props} type="button" class="cds--definition-term">{value.text}</button>
                  {/snippet}
                </Tooltip>
              {/if}
            </td>
          {/each}
        </tr>
      {/each}
    {/snippet}
  </DataTable>
</ScrollRegion>
