<!-- Parameter sweep page (docs/architecture/backtest.md section 10.11.4): a workbench like the backtest page. URL:
     /sweeps/<id>; /sweeps opens the newest sweep.
     Left: the "Parameter sweeps" side column with the "New parameter sweep" button and the sweep list (status icon before
     the number, strategy version, finished runs / all runs). Top panel: the run count of each status (a status icon with
     the status in its tooltip, then the count), the "Metric" select (and the
     select of the third parameter value), and the chart: points for 1 parameter, a heatmap for 2 or 3. Each heatmap
     cell shows its value on a Carbon sequential color. Bottom panel "Runs": the parameter values, the status icon, and
     the key metrics of each run. Each column sorts the rows, and a click on a row opens its backtest. The page reads the
     sweep and the list again while a run is queued or running.
     Right: the "AI assistant" side column (routes/assistant/, docs/architecture/assistant.md 25.12). -->
<script lang="ts">
  import Add16 from '@carbon/icons/es/add/16.js';
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { navigating, page } from '$app/state';
  import { describeBacktestStatus, findBacktestStatusKind } from '#lib/backtest';
  import {
    DataTable,
    IconButton,
    InlineNotification,
    readSequentialColor,
    Select,
    SortHeader,
    StatusIndicator,
    type TableColumn,
  } from '#lib/foundation/carbon';
  import { EmptyText } from '#lib/foundation/empty_text';
  import { startPolling } from '#lib/foundation/polling';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { Panel, PanelSplit, SideColumn, Workbench, type PanelSpec } from '#lib/foundation/workbench';
  import { formatVersionLabel } from '#lib/strategy';
  import {
    DEFAULT_SWEEP_METRIC,
    formatSweepMetric,
    listSweeps,
    readParameterNames,
    readSweep,
    readSweepChart,
    readSweepRows,
    readSweepStatus,
    sortSweepRows,
    SWEEP_METRICS,
    SWEEP_STATUS_COLUMN,
    type ParameterValue,
    type SortDirection,
    type Sweep,
    type SweepDetail,
    type SweepMetricKey,
  } from '#lib/sweep';
  import StartSweepDialog from '../StartSweepDialog.svelte';
  import SweepPointChart from '../SweepPointChart.svelte';
  import AssistantColumn from '../../assistant/AssistantColumn.svelte';

  const CHECK_INTERVAL_MILLISECONDS = 2000;
  const PANELS: PanelSpec[] = [
    { id: 'overview', minPixels: 160 },
    { id: 'runs', minPixels: 96, defaultPixels: 280, splitterLabel: 'Resize the overview and the runs' },
  ];
  const STATUS_LINE = ['finished', 'failed', 'running', 'queued'] as const;
  const LIST_COLUMNS: TableColumn[] = [
    { header: '#', align: 'right' },
    { header: 'Strategy' },
    { header: 'Runs', align: 'right' },
  ];

  const routeSweepId = $derived(page.params['sweepId']);
  const sweepId = $derived(routeSweepId === undefined ? null : Number(routeSweepId));

  let sweeps = $state<Sweep[]>([]);
  let isListRead = $state(false);
  let listMessage = $state('');
  let listReadCount = $state(0);
  let sweep = $state<SweepDetail | null>(null);
  let detailMessage = $state('');
  let metric = $state<SweepMetricKey>(DEFAULT_SWEEP_METRIC);
  let sliceValue = $state<ParameterValue | null>(null);
  let sortColumn = $state<string>(DEFAULT_SWEEP_METRIC);
  let sortDirection = $state<SortDirection>('descending');
  let isStartDialogOpen = $state(false);

  const shownSweep = $derived(sweep !== null && sweep.id === sweepId ? sweep : null);
  const parameterNames = $derived(shownSweep === null ? [] : readParameterNames(shownSweep));
  const chart = $derived(shownSweep === null ? null : readSweepChart(shownSweep, metric, sliceValue));
  const metricLabel = $derived(SWEEP_METRICS.find((item) => item.value === metric)?.label ?? '');
  const sortedRows = $derived(
    shownSweep === null ? [] : sortSweepRows(readSweepRows(shownSweep), sortColumn, sortDirection),
  );

  function isRunning(statusCounts: Record<string, number>): boolean {
    return (statusCounts['queued'] ?? 0) + (statusCounts['running'] ?? 0) > 0;
  }

  $effect(() => {
    listReadCount satisfies number;
    return startPolling(
      () => listSweeps(fetch),
      (result) => {
        isListRead = true;
        if (result.kind === 'failed') {
          listMessage = result.message;
          return true;
        }
        listMessage = '';
        sweeps = result.value;
        return result.value.some((item) => isRunning(item.status_counts));
      },
      CHECK_INTERVAL_MILLISECONDS,
      (message) => {
        listMessage = message;
      },
    );
  });

  // /sweeps opens the newest sweep, like /backtests.
  $effect(() => {
    const newest = sweeps[0];
    if (navigating.to === null && sweepId === null && newest !== undefined) {
      void goto(resolve('/sweeps/[[sweepId]]', { sweepId: String(newest.id) }), { replace: true, reset: false });
    }
  });

  $effect(() => {
    if (sweepId === null) {
      return;
    }
    const id = sweepId;
    return startPolling(
      () => readSweep(fetch, id),
      (result) => {
        if (result.kind === 'failed') {
          detailMessage = result.message;
          return true;
        }
        detailMessage = '';
        sweep = result.value;
        return isRunning(result.value.status_counts);
      },
      CHECK_INTERVAL_MILLISECONDS,
      (message) => {
        detailMessage = message;
      },
    );
  });

  function sortBy(column: string): void {
    if (sortColumn === column) {
      sortDirection = sortDirection === 'descending' ? 'ascending' : 'descending';
    } else {
      sortColumn = column;
      sortDirection = 'descending';
    }
  }

  function backtestHref(backtestId: number): string {
    return resolve('/backtests/[[backtestId]]', { backtestId: String(backtestId) });
  }

  function openRun(event: MouseEvent, backtestId: number): void {
    if (event.target instanceof Element && event.target.closest('a') !== null) {
      return;
    }
    // eslint-disable-next-line svelte/no-navigation-without-resolve -- backtestHref resolves the path.
    void goto(backtestHref(backtestId));
  }

  function openStartedSweep(started: SweepDetail): void {
    listReadCount += 1;
    void goto(resolve('/sweeps/[[sweepId]]', { sweepId: String(started.id) }));
  }
</script>

<Workbench>
  <SideColumn label="Parameter sweeps" side="start" width="28rem" storageKey="atrade.sweep-page.list-column">
    {#snippet actions()}
      <IconButton
        label="New parameter sweep"
        icon={Add16}
        onclick={() => {
          isStartDialogOpen = true;
        }}
      />
    {/snippet}
    {#if listMessage !== ''}
      <InlineNotification kind="error" title="Parameter sweeps not read" subtitle={listMessage} lowContrast />
    {:else}
      <div class="table-region sweep-list">
        <ScrollRegion label="Parameter sweep list" fill>
          <DataTable columns={LIST_COLUMNS} size="sm">
            {#snippet rows()}
              {#each sweeps as item (item.id)}
                {@const status = readSweepStatus(item.status_counts)}
                <tr
                  class={['link-row', item.id === sweepId && 'cds--data-table--selected']}
                  onclick={(event) => {
                    if (!(event.target instanceof Element && event.target.closest('a') !== null)) {
                      void goto(resolve('/sweeps/[[sweepId]]', { sweepId: String(item.id) }));
                    }
                  }}
                >
                  <th scope="row" align="right">
                    <StatusIndicator label={describeBacktestStatus(status)} kind={findBacktestStatusKind(status)} align="right" />
                    <a
                      class="row-link"
                      href={resolve('/sweeps/[[sweepId]]', { sweepId: String(item.id) })}
                      aria-current={item.id === sweepId ? 'page' : undefined}>#{item.id}</a
                    >
                  </th>
                  <td>
                    <span class="ellipsis" title={formatVersionLabel(item.strategy_name, item.version_number)}
                      >{formatVersionLabel(item.strategy_name, item.version_number)}</span
                    >
                  </td>
                  <td align="right">{item.status_counts['finished'] ?? 0} / {item.run_count}</td>
                </tr>
              {/each}
            {/snippet}
          </DataTable>
        </ScrollRegion>
      </div>
    {/if}
  </SideColumn>

  {#if shownSweep === null || chart === null}
    <div class="empty-main">
      {#if detailMessage !== ''}
        <InlineNotification kind="error" title="Parameter sweep not read" subtitle={detailMessage} lowContrast />
      {:else if isListRead && sweeps.length === 0 && listMessage === ''}
        <EmptyText text="No parameter sweeps" />
      {/if}
    </div>
  {:else}
    {@const detail = shownSweep}
    {@const shownChart = chart}
    <PanelSplit storageKey="atrade.sweep-page.panel-split" panels={PANELS}>
      {#snippet panel(id, state)}
        {#if id === 'overview'}
          <Panel {...state} label={`Parameter sweep #${String(detail.id)}`}>
            {#snippet header()}
              <h1 class="run-title">
                <span class="run-number">#{detail.id}</span>
                <a
                  class="cds--link"
                  href={resolve('/strategies/[strategyId]/versions/[versionNumber]', {
                    strategyId: String(detail.strategy_id),
                    versionNumber: String(detail.version_number),
                  })}>{formatVersionLabel(detail.strategy_name, detail.version_number)}</a
                >
              </h1>
              <span class="status-line" role="status" aria-label="Run counts">
                {#each STATUS_LINE as status (status)}
                  <span class="status-count"
                    ><StatusIndicator label={describeBacktestStatus(status)} kind={findBacktestStatusKind(status)} />{String(
                      detail.status_counts[status] ?? 0,
                    )}</span
                  >
                {/each}
              </span>
            {/snippet}
            <div class="chart-toolbar">
              <Select
                label="Metric"
                size="sm"
                items={[...SWEEP_METRICS]}
                value={metric}
                onValueChange={(value: SweepMetricKey) => {
                  metric = value;
                }}
              />
              {#if shownChart.kind === 'heatmap' && shownChart.slice !== null}
                {@const slice = shownChart.slice}
                <Select
                  label={slice.parameter}
                  size="sm"
                  items={slice.values.map((value) => ({ value: String(value), label: String(value) }))}
                  value={String(slice.value)}
                  onValueChange={(value: string) => {
                    sliceValue = slice.values.find((item) => String(item) === value) ?? null;
                  }}
                />
              {/if}
            </div>
            {#if shownChart.kind === 'points'}
              <div class="point-chart">
                <SweepPointChart parameter={shownChart.parameter} points={shownChart.points} {metric} {metricLabel} />
              </div>
            {:else}
              {@const heatmap = shownChart.heatmap}
              <div class="table-region">
                <ScrollRegion label="Heatmap" fill>
                  <table class="cds--data-table cds--data-table--xs heatmap" aria-label={`${metricLabel} heatmap`}>
                    <thead>
                      <tr>
                        <th scope="col"><div class="cds--table-header-label">{shownChart.rowParameter} \ {shownChart.columnParameter}</div></th>
                        {#each heatmap.columns as column (column)}
                          <th scope="col" align="right"><div class="cds--table-header-label">{String(column)}</div></th>
                        {/each}
                      </tr>
                    </thead>
                    <tbody>
                      {#each heatmap.rows as row, rowIndex (row)}
                        <tr>
                          <th scope="row" align="right">{String(row)}</th>
                          {#each heatmap.cells[rowIndex] ?? [] as cell, columnIndex (columnIndex)}
                            {#if cell === null}
                              <td align="right">{formatSweepMetric(metric, null)}</td>
                            {:else}
                              {@const color = readSequentialColor(heatmap.step(cell))}
                              <td align="right" style:background-color={color.background} style:color={color.text}
                                >{formatSweepMetric(metric, cell)}</td
                              >
                            {/if}
                          {/each}
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                </ScrollRegion>
              </div>
            {/if}
          </Panel>
        {:else}
          <Panel {...state} label="Runs">
            <div class="table-region">
              <ScrollRegion label="Runs" fill>
                <div class="cds--data-table-container">
                  <table class="cds--data-table cds--data-table--sm cds--data-table--sort runs">
                    <thead>
                      <tr>
                        {#each parameterNames as name (name)}
                          <SortHeader
                            label={name}
                            align="right"
                            direction={sortColumn === name ? sortDirection : null}
                            onSort={() => {
                              sortBy(name);
                            }}
                          />
                        {/each}
                        <SortHeader
                          label="Status"
                          direction={sortColumn === SWEEP_STATUS_COLUMN ? sortDirection : null}
                          onSort={() => {
                            sortBy(SWEEP_STATUS_COLUMN);
                          }}
                        />
                        {#each SWEEP_METRICS as item (item.value)}
                          <SortHeader
                            label={item.label}
                            align="right"
                            direction={sortColumn === item.value ? sortDirection : null}
                            onSort={() => {
                              sortBy(item.value);
                            }}
                          />
                        {/each}
                      </tr>
                    </thead>
                    <tbody>
                      {#each sortedRows as row (row.backtestId)}
                        <tr
                          class="link-row"
                          onclick={(event) => {
                            openRun(event, row.backtestId);
                          }}
                        >
                          {#each parameterNames as name, index (name)}
                            <td align="right">
                              {#if index === 0}
                                <a class="row-link" href={resolve('/backtests/[[backtestId]]', { backtestId: String(row.backtestId) })}>{String(row.values[name])}</a>
                              {:else}
                                {String(row.values[name])}
                              {/if}
                            </td>
                          {/each}
                          <td>
                            <StatusIndicator label={describeBacktestStatus(row.status)} kind={findBacktestStatusKind(row.status)} />
                          </td>
                          {#each SWEEP_METRICS as item (item.value)}
                            <td align="right">{formatSweepMetric(item.value, (row.values[item.value] ?? null) as number | null)}</td>
                          {/each}
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                </div>
              </ScrollRegion>
            </div>
          </Panel>
        {/if}
      {/snippet}
    </PanelSplit>
  {/if}

  <AssistantColumn />
</Workbench>

<StartSweepDialog
  open={isStartDialogOpen}
  onOpenChange={(open: boolean) => {
    isStartDialogOpen = open;
  }}
  onStarted={openStartedSweep}
/>

<style>
  .empty-main {
    flex: 1;
    min-inline-size: 0;
  }

  .table-region {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-block-size: 0;
  }

  .table-region :global(thead th) {
    position: sticky;
    inset-block-start: 0;
    z-index: 1;
  }

  .table-region :global(td[align='right']),
  .table-region :global(th[align='right']) {
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }

  /* Fixed column widths: the tables are never wider than their region. Long text ends with an ellipsis. */
  .sweep-list :global(table),
  .runs {
    table-layout: fixed;
  }

  /* The status icon and the number. */
  .sweep-list :global(th:nth-child(1)) {
    inline-size: var(--cds-spacing-12);
  }

  .sweep-list :global(th:nth-child(3)) {
    inline-size: var(--cds-spacing-11);
  }

  .sweep-list :global(:is(td, th)),
  .runs :global(:is(td, th)),
  .runs :global(.cds--table-header-label) {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* The cell color shows at once when the metric changes: no Carbon background transition. */
  .heatmap td {
    transition: none;
  }

  .heatmap tbody th {
    background-color: transparent;
  }

  .ellipsis {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .link-row {
    cursor: pointer;
  }

  .row-link {
    color: inherit;
    font-variant-numeric: tabular-nums;
    text-decoration: none;
  }

  .row-link:focus-visible {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }

  .run-title {
    display: flex;
    align-items: baseline;
    gap: var(--cds-spacing-04);
  }

  .run-title > :global(*) {
    font: inherit;
    letter-spacing: inherit;
  }

  .run-number {
    font-variant-numeric: tabular-nums;
    color: var(--cds-text-secondary);
  }

  .status-line {
    display: flex;
    flex: none;
    gap: var(--cds-spacing-05);
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }

  .chart-toolbar {
    display: flex;
    flex: none;
    gap: var(--cds-spacing-05);
    padding: var(--cds-spacing-03) var(--cds-spacing-05);
  }

  .chart-toolbar > :global(*) {
    inline-size: 12rem;
  }

  .point-chart {
    flex: 1;
    min-block-size: 0;
    padding: var(--cds-spacing-03) var(--cds-spacing-05);
  }

  .heatmap {
    inline-size: auto;
  }
</style>
