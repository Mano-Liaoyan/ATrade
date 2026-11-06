<!-- Parameter sweep page (docs/architecture/backtest.md section 10.11.4): a workbench like the backtest page. URL:
     /sweeps/<id>; /sweeps opens the newest sweep.
     Left: the "Parameter sweeps" side column with the "New parameter sweep" button and the sweep list (status icon before
     the number, strategy version, finished runs / all runs). Top panel: the run count of each status (a status icon with
     the status in its tooltip, then the count), the "Metric" select (and the
     select of the third parameter value), and the chart: points for 1 parameter, a heatmap for 2 or 3. Each heatmap
     cell shows its value on a Carbon sequential color. Bottom panel "Runs": the parameter values, the status icon, and
     the key metrics of each run. Each column sorts the rows, and a click on a row opens its backtest. A right-click on
     a sweep row opens its context menu ("Open in new tab"). The page reads the
     list again after each change that /ws/sweeps pushes, and the open sweep when its list row changes. The
     "Delete parameter sweep" button opens a danger dialog; the backend can refuse the delete, and the page shows the reason.
     Right: the "AI assistant" side column (routes/assistant/, docs/architecture/assistant.md 25.12). -->
<script lang="ts">
  import Add16 from '@carbon/icons/es/add/16.js';
  import TrashCan16 from '@carbon/icons/es/trash-can/16.js';
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import { describeBacktestStatus, findBacktestStatusKind } from '#lib/backtest';
  import {
    ContextMenu,
    DataTable,
    Dialog,
    IconButton,
    InlineNotification,
    readSequentialColor,
    Select,
    SortHeader,
    StatusIndicator,
    type ContextMenuItem,
    type TableColumn,
  } from '#lib/foundation/carbon';
  import { EmptyText } from '#lib/foundation/empty_text';
  import { HorizontalScrollTrack, ScrollRegion } from '#lib/foundation/scroll_region';
  import { Panel, PanelSplit, SideColumn, Workbench, type PanelSpec } from '#lib/foundation/workbench';
  import { formatVersionLabel } from '#lib/strategy';
  import {
    DEFAULT_SWEEP_METRIC,
    SWEEPS_SOCKET_PATH,
    deleteSweep,
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
  import { RunWorkbench } from '../../run_workbench.svelte';
  import RunCenter from '../../RunCenter.svelte';

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

  // /ws/sweeps pushes each change of a sweep or of one of its runs. The open sweep reads again when its list row changes
  // (the run counts).
  const workbench = new RunWorkbench<Sweep, SweepDetail>({
    socketPath: SWEEPS_SOCKET_PATH,
    list: () => listSweeps(fetch),
    readDetail: (id) => readSweep(fetch, id),
    href: (id) => resolve('/sweeps/[[sweepId]]', { sweepId: String(id) }),
    openId: () => sweepId,
  });
  let metric = $state<SweepMetricKey>(DEFAULT_SWEEP_METRIC);
  let sliceValue = $state<ParameterValue | null>(null);
  let sortColumn = $state<string>(DEFAULT_SWEEP_METRIC);
  let sortDirection = $state<SortDirection>('descending');
  let isDeleteDialogOpen = $state(false);
  let isDeleting = $state(false);
  const runsColumnsId = $props.id();
  let runsColumns = $state<HTMLDivElement>();
  let runsTable = $state<HTMLTableElement>();
  let deleteMessage = $state('');

  const shownSweep = $derived(workbench.detail !== null && workbench.detail.id === sweepId ? workbench.detail : null);
  const parameterNames = $derived(shownSweep === null ? [] : readParameterNames(shownSweep));
  const chart = $derived(shownSweep === null ? null : readSweepChart(shownSweep, metric, sliceValue));
  const metricLabel = $derived(SWEEP_METRICS.find((item) => item.value === metric)?.label ?? '');
  const sortedRows = $derived(
    shownSweep === null ? [] : sortSweepRows(readSweepRows(shownSweep), sortColumn, sortDirection),
  );

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

  function readMenuItems(key: string): ContextMenuItem[] {
    const href = resolve('/sweeps/[[sweepId]]', { sweepId: key });
    return [
      {
        label: 'Open in new tab',
        onSelect: () => {
          window.open(href, '_blank', 'noopener');
        },
      },
    ];
  }

  // After a delete, /sweeps opens the newest sweep that is left.
  async function deleteOpenSweep(id: number): Promise<void> {
    isDeleting = true;
    const result = await deleteSweep(fetch, id);
    isDeleting = false;
    isDeleteDialogOpen = false;
    if (result.kind === 'failed') {
      deleteMessage = result.message;
      return;
    }
    deleteMessage = '';
    workbench.removeItem(id);
    await goto(resolve('/sweeps/[[sweepId]]', { sweepId: undefined }), { replace: true });
  }

  function openStartedSweep(started: SweepDetail): void {
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
          workbench.isStartDialogOpen = true;
        }}
      />
    {/snippet}
    <div class="table-region sweep-list">
      <ContextMenu readLabel={(key: string) => `Parameter sweep #${key}`} readItems={readMenuItems}>
        <ScrollRegion label="Parameter sweep list" fill>
          <DataTable columns={LIST_COLUMNS} size="sm">
            {#snippet rows()}
              {#each workbench.items as item (item.id)}
                {@const status = readSweepStatus(item.status_counts)}
                <tr
                  data-context-key={item.id}
                  class={['link-row', item.id === sweepId && 'cds--data-table--selected']}
                  onclick={(event) => {
                    if (!(event.target instanceof Element && event.target.closest('a') !== null)) {
                      void goto(resolve('/sweeps/[[sweepId]]', { sweepId: String(item.id) }));
                    }
                  }}
                >
                  <th scope="row" align="right">
                    <span class="status-id">
                      <StatusIndicator label={describeBacktestStatus(status)} kind={findBacktestStatusKind(status)} align="right" />
                      <a
                        class="row-link"
                        href={resolve('/sweeps/[[sweepId]]', { sweepId: String(item.id) })}
                        aria-current={item.id === sweepId ? 'page' : undefined}>#{item.id}</a
                      >
                    </span>
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
      </ContextMenu>
    </div>
  </SideColumn>

  <RunCenter {workbench} listTitle="Parameter sweeps not read" detailTitle="Parameter sweep not read">
    {#if deleteMessage !== ''}
      <InlineNotification
        kind="error"
        title="Parameter sweep not deleted"
        subtitle={deleteMessage}
        lowContrast
        onClose={() => {
          deleteMessage = '';
        }}
      />
    {/if}
    {#if shownSweep === null || chart === null}
      <div class="atrade-run-empty">
        {#if workbench.isListRead && workbench.items.length === 0 && workbench.listMessage === '' && workbench.detailMessage === ''}
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
                <h1 class="atrade-run-title">
                  <span class="atrade-run-number">#{detail.id}</span>
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
                <IconButton
                  label="Delete parameter sweep"
                  icon={TrashCan16}
                  onclick={() => {
                    isDeleteDialogOpen = true;
                  }}
                />
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
                  <div class="cds--data-table-content runs-columns" id={runsColumnsId} bind:this={runsColumns}>
                    <table class="cds--data-table cds--data-table--sm cds--data-table--sort runs" bind:this={runsTable}>
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
                <HorizontalScrollTrack label="Runs columns" viewport={runsColumns} content={runsTable} viewportId={runsColumnsId} wheelScrolls={false} />
              </div>
            </Panel>
          {/if}
        {/snippet}
      </PanelSplit>
    {/if}
  </RunCenter>

  <AssistantColumn />
</Workbench>

<StartSweepDialog
  open={workbench.isStartDialogOpen}
  onOpenChange={workbench.changeStartDialog}
  onStarted={openStartedSweep}
/>

{#if sweepId !== null}
  {@const id = sweepId}
  <Dialog
    open={isDeleteDialogOpen}
    onOpenChange={(open: boolean) => {
      isDeleteDialogOpen = open;
    }}
    title={`Delete parameter sweep #${String(id)}?`}
    primaryText="Delete parameter sweep"
    primaryKind="danger"
    busy={isDeleting}
    onPrimary={() => {
      void deleteOpenSweep(id);
    }}
  />
{/if}

<style>
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

  /* Fixed column widths. Long text ends with an ellipsis. */
  .sweep-list :global(table),
  .runs {
    table-layout: fixed;
  }

  /* All Runs columns stay readable: a narrow region scrolls them sideways with its own track. The sideways scroll makes
     the header scroll away with the rows. */
  .runs {
    min-inline-size: 54rem;
  }

  .runs-columns {
    scrollbar-width: none;
  }

  .runs-columns::-webkit-scrollbar {
    display: none;
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

  /* The status icon keeps the start of the cell and the number keeps the end, so the icons are in one line for
     each number length. */
  .status-id {
    display: flex;
    align-items: center;
    gap: var(--cds-spacing-03);
  }

  .status-id > a {
    margin-inline-start: auto;
    font-variant-numeric: tabular-nums;
  }
</style>
