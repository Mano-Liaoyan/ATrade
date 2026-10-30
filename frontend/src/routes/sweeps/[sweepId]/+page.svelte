<!-- Parameter sweep page (docs/architecture/backtest.md section 10.11.4): a workbench like the backtest page.
     Left: the "Parameter sweeps" side column. Top panel: the status line and, for 2 parameters, the Total return
     heatmap. Bottom panel: the "Runs" table; each column sorts the rows, and a row opens its backtest.
     Not done yet (#204): the "New parameter sweep" dialog, the "Metric" select, the dot chart, the 3-parameter select,
     the Carbon sequential cell color. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import { EmptyText } from '#lib/foundation/empty_text';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { Panel, PanelSplit, SideColumn, Workbench, type PanelSpec } from '#lib/foundation/workbench';
  import {
    listSweeps,
    readHeatmap,
    readSweep,
    sortSweepRows,
    type SortDirection,
    type Sweep,
    type SweepDetail,
    type SweepRow,
  } from '#lib/sweep';

  const PANELS: PanelSpec[] = [
    { id: 'overview', minPixels: 160 },
    { id: 'runs', minPixels: 96, defaultPixels: 280, splitterLabel: 'Resize the overview and the runs' },
  ];
  const METRIC = 'total_return_percent';
  const STATUSES = ['completed', 'failed', 'running', 'queued'];
  const HEATMAP_PARAMETER_COUNT = 2;
  const VALUE_DECIMALS = 2;

  let sweeps = $state<Sweep[]>([]);
  let sweep = $state<SweepDetail | null>(null);
  let sortColumn = $state(METRIC);
  let sortDirection = $state<SortDirection>('descending');

  const sweepId = $derived(Number(page.params.sweepId));
  const parameterNames = $derived(
    sweep === null ? [] : sweep.grid.map((entry) => String(entry.name)),
  );
  const rows = $derived<SweepRow[]>(
    sweep === null
      ? []
      : sweep.runs.map((run) => ({
          backtestId: run.backtest_id,
          values: {
            ...run.parameters,
            [METRIC]: run.metrics === null ? null : Number(run.metrics.total_return_percent),
          },
        })),
  );
  const sortedRows = $derived(sortSweepRows(rows, sortColumn, sortDirection));
  const heatmap = $derived(
    parameterNames.length === HEATMAP_PARAMETER_COUNT
      ? readHeatmap(
          rows.map((row) => ({ parameters: row.values as Record<string, number>, value: row.values[METRIC] as number | null })),
          parameterNames[0] ?? '',
          parameterNames[1] ?? '',
        )
      : null,
  );

  $effect(() => {
    void listSweeps(fetch).then((result) => {
      if (result.kind === 'ok') {
        sweeps = result.value;
      }
    });
  });

  $effect(() => {
    const id = sweepId;
    void readSweep(fetch, id).then((result) => {
      sweep = result.kind === 'ok' ? result.value : null;
    });
  });

  function sortBy(column: string): void {
    if (sortColumn === column) {
      sortDirection = sortDirection === 'descending' ? 'ascending' : 'descending';
    } else {
      sortColumn = column;
      sortDirection = 'descending';
    }
  }
</script>

<Workbench>
  <SideColumn label="Parameter sweeps" side="start" width="28rem" storageKey="atrade.sweep-page.list-column">
    <ScrollRegion label="Parameter sweeps" fill>
      <ul class="cds--list--unordered sweep-list">
        {#each sweeps as item (item.id)}
          <li>
            <a class="cds--link" href={resolve('/sweeps/[sweepId]', { sweepId: String(item.id) })}>#{item.id}</a>
            <span class="number">{item.status_counts['completed'] ?? 0} / {item.run_count}</span>
          </li>
        {/each}
      </ul>
    </ScrollRegion>
  </SideColumn>

  {#if sweep === null}
    <EmptyText text="No parameter sweep" />
  {:else}
    {@const detail = sweep}
    <PanelSplit storageKey="atrade.sweep-page.panel-split" panels={PANELS}>
      {#snippet panel(id, state)}
        {#if id === 'overview'}
          <Panel {...state} label={`Parameter sweep #${String(detail.id)}`}>
            <p class="status-line" role="status">
              {#each STATUSES as status (status)}
                <span class="number">{detail.status_counts[status] ?? 0} {status}</span>
              {/each}
            </p>
            {#if heatmap !== null}
              <ScrollRegion label="Heatmap" fill>
                <table class="cds--data-table cds--data-table--sm heatmap">
                  <thead>
                    <tr>
                      <th>{parameterNames[1]} \ {parameterNames[0]}</th>
                      {#each heatmap.columns as column (column)}<th class="number">{column}</th>{/each}
                    </tr>
                  </thead>
                  <tbody>
                    {#each heatmap.rows as row, rowIndex (row)}
                      <tr>
                        <th class="number">{row}</th>
                        {#each heatmap.cells[rowIndex] ?? [] as cell, columnIndex (columnIndex)}
                          <td class="number">{cell === null ? '' : cell.toFixed(VALUE_DECIMALS)}</td>
                        {/each}
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </ScrollRegion>
            {/if}
          </Panel>
        {:else}
          <Panel {...state} label="Runs">
            <ScrollRegion label="Runs" fill>
              <table class="cds--data-table cds--data-table--sm cds--data-table--sort">
                <thead>
                  <tr>
                    {#each [...parameterNames, METRIC] as column (column)}
                      <th class="number" aria-sort={sortColumn === column ? sortDirection : 'none'}>
                        <button class="cds--table-sort" type="button" onclick={() => { sortBy(column); }}>
                          <span class="cds--table-sort__flex">{column === METRIC ? 'Total return' : column}</span>
                        </button>
                      </th>
                    {/each}
                  </tr>
                </thead>
                <tbody>
                  {#each sortedRows as row (row.backtestId)}
                    <tr>
                      {#each [...parameterNames, METRIC] as column (column)}
                        <td class="number">
                          <a class="cds--link" href={resolve('/backtests/[[backtestId]]', { backtestId: String(row.backtestId) })}
                            >{row.values[column] ?? ''}</a
                          >
                        </td>
                      {/each}
                    </tr>
                  {/each}
                </tbody>
              </table>
            </ScrollRegion>
          </Panel>
        {/if}
      {/snippet}
    </PanelSplit>
  {/if}
</Workbench>

<style>
  .number {
    font-variant-numeric: tabular-nums;
    text-align: right;
  }

  .sweep-list li {
    display: flex;
    justify-content: space-between;
    padding: var(--cds-spacing-03) var(--cds-spacing-05);
  }

  .status-line {
    display: flex;
    gap: var(--cds-spacing-05);
    padding: var(--cds-spacing-03) var(--cds-spacing-05);
  }
</style>
