<!-- A forward test compared with a backtest of the same period (docs/architecture/forward_test.md section 12.10): a
     workbench (foundation/workbench, spec #99) with the structure of the forward test page. Left: the "Forward tests"
     side column (ForwardTestList, live from /ws/forward-tests). Center: the comparison panel (header line: the name,
     the strategy version, the instrument, and the backtest status; then one key metric row for each test and both
     equity and drawdown curves on one time axis with the interruptions in grey) over the Fills / Logs panel. Fills
     compares the fills of both tests; Logs shows the backtest error. The page reads the comparison, the forward test
     fills, and the backtest trades again every 2 seconds until the backtest has its final status. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import {
    ComparedKeyMetrics,
    describeBacktestStatus,
    EquityDrawdownChart,
    findBacktestStatusKind,
    isFinalStatus,
    readBacktest,
    type ComparedTest,
    type DrawdownCurve,
    type TestTrade,
  } from '#lib/backtest';
  import { InlineNotification, StatusIndicator } from '#lib/foundation/carbon';
  import { EmptyText } from '#lib/foundation/empty_text';
  import { LiveUpdatesNotification } from '#lib/foundation/live_socket';
  import { startPolling } from '#lib/foundation/polling';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatBarPeriod } from '#lib/foundation/value_format';
  import { Panel, PanelSplit, SideColumn, Workbench, type PanelSpec } from '#lib/foundation/workbench';
  import {
    FillComparisonTable,
    ForwardTestsOnInstrumentsFeed,
    readForwardTestComparison,
    readForwardTestDetail,
    type ForwardTestComparison,
  } from '#lib/forward_test';
  import { formatVersionLabel } from '#lib/strategy';
  import { createInstrumentHref } from '../../../../instrument_href';
  import ForwardTestList from '../../../ForwardTestList.svelte';

  const READ_INTERVAL_MILLISECONDS = 2000;
  // The panels of the forward test page. The chart panel has a higher minimum: the header line, the 2 metric rows (they
  // scroll when they do not fit), and the chart.
  const PANELS: PanelSpec[] = [
    { id: 'chart', minPixels: 256 },
    { id: 'tables', minPixels: 96, defaultPixels: 240, splitterLabel: 'Resize the chart and the tables' },
  ];
  type ComparisonTable = 'fills' | 'logs';
  const TABLE_TABS: { value: ComparisonTable; label: string }[] = [
    { value: 'fills', label: 'Fills' },
    { value: 'logs', label: 'Logs' },
  ];

  const forwardTestId = $derived(Number(page.params['forwardTestId']));
  const backtestId = $derived(Number(page.params['backtestId']));
  const title = $derived(`Compare forward test #${String(forwardTestId)} with backtest #${String(backtestId)}`);

  // The one /ws/forward-tests socket of the page: the list.
  const feed = new ForwardTestsOnInstrumentsFeed();
  let comparison = $state<ForwardTestComparison | null>(null);
  // The fills of the forward test and the trades of the backtest: the win rates come from them.
  let forwardTestFills = $state<TestTrade[]>([]);
  let backtestTrades = $state<TestTrade[]>([]);
  let errorMessage = $state('');
  // The read error of the forward test fills or the backtest trades: the win rates are not known then.
  let tradeMessage = $state('');
  let selectedTable: ComparisonTable = $state('fills');

  const comparedTests = $derived.by<ComparedTest[]>(() => {
    if (comparison === null) {
      return [];
    }
    const { forward_test: forwardTest, backtest } = comparison;
    return [
      {
        name: `Forward test #${String(forwardTest.id)} ${formatVersionLabel(forwardTest.strategy_name, forwardTest.version_number)}`,
        href: resolve('/forward-tests/[[forwardTestId]]', { forwardTestId: String(forwardTest.id) }),
        metrics: comparison.forward_test_metrics,
        startCapitalUsd: forwardTest.start_balance_usd,
        trades: forwardTestFills,
        // The forward test metrics of the comparison cover the backtest period only.
        period: backtest,
      },
      {
        name: `Backtest #${String(backtest.id)}`,
        href: resolve('/backtests/[[backtestId]]', { backtestId: String(backtest.id) }),
        metrics: backtest.metrics,
        startCapitalUsd: backtest.paper_capital_usd,
        trades: backtestTrades,
      },
    ];
  });

  const comparedCurves = $derived<DrawdownCurve[]>(
    comparison === null
      ? []
      : [comparison.forward_test_equity_curve, comparison.backtest_equity_curve].map((points, index) => ({
          name: comparedTests[index]?.name ?? '',
          points,
          startCapitalUsd: comparedTests[index]?.startCapitalUsd ?? null,
        })),
  );

  $effect(() => feed.start(window.location));

  $effect(() => {
    const currentForwardTestId = forwardTestId;
    const currentBacktestId = backtestId;
    return startPolling(
      () =>
        Promise.all([
          readForwardTestComparison(fetch, currentForwardTestId, currentBacktestId),
          readForwardTestDetail(fetch, currentForwardTestId),
          readBacktest(fetch, currentBacktestId),
        ]),
      ([result, forwardTestResult, backtestResult]) => {
        if (result.kind === 'failed') {
          errorMessage = result.message;
          return true;
        }
        errorMessage = '';
        comparison = result.value;
        if (forwardTestResult.kind === 'ok') {
          forwardTestFills = forwardTestResult.value.fills;
        }
        if (backtestResult.kind === 'ok') {
          backtestTrades = backtestResult.value.trades;
        }
        const failedTradeRead = [forwardTestResult, backtestResult].find((read) => read.kind === 'failed');
        tradeMessage = failedTradeRead?.kind === 'failed' ? failedTradeRead.message : '';
        return !isFinalStatus(result.value.backtest.status);
      },
      READ_INTERVAL_MILLISECONDS,
      (message) => {
        errorMessage = message;
      },
    );
  });
</script>

<Workbench>
  <SideColumn label="Forward tests" side="start" width="30rem" storageKey="atrade.forward-test-page.list-column">
    <LiveUpdatesNotification isConnected={feed.isConnected} />
    <ForwardTestList forwardTests={feed.forwardTests} openForwardTestId={forwardTestId} />
  </SideColumn>

  {#if comparison === null}
    <div class="empty-main">
      {#if errorMessage !== ''}
        <InlineNotification kind="error" title="Forward test not compared" subtitle={errorMessage} lowContrast />
      {/if}
    </div>
  {:else}
    {@const compared = comparison}
    {@const forwardTest = compared.forward_test}
    <PanelSplit storageKey="atrade.forward-test-comparison-page.panel-split" panels={PANELS}>
      {#snippet panel(id, state)}
        {#if id === 'chart'}
          <Panel {...state} label={title}>
            {#snippet header()}
              <h1 class="run-title">
                <span>{title}</span>
                <a
                  class="cds--link"
                  href={resolve('/strategies/[strategyId]', { strategyId: String(forwardTest.strategy_id) })}
                  >{formatVersionLabel(forwardTest.strategy_name, forwardTest.version_number)}</a
                >
                <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- createInstrumentHref resolves the path. -->
                <a class="cds--link" href={createInstrumentHref(forwardTest)}>{forwardTest.symbol}</a>
                <span class="run-period">{formatBarPeriod(forwardTest.bar_period)}</span>
              </h1>
              <span class="run-status" role="status" aria-label="Backtest status">
                <StatusIndicator
                  label={describeBacktestStatus(compared.backtest.status)}
                  kind={findBacktestStatusKind(compared.backtest.status)}
                />
              </span>
            {/snippet}
            {#if tradeMessage !== ''}
              <InlineNotification kind="error" title="Win rates not read" subtitle={tradeMessage} lowContrast />
            {/if}
            <div class="compare-area">
              <div class="metrics">
                <ComparedKeyMetrics tests={comparedTests} />
              </div>
              <div class="chart">
                <EquityDrawdownChart
                  curves={comparedCurves}
                  label="Equity and drawdown"
                  interruptions={compared.interruptions}
                  fill
                />
              </div>
            </div>
          </Panel>
        {:else}
          <Panel
            {...state}
            label="Comparison tables"
            tabs={{
              label: 'Comparison tables',
              items: TABLE_TABS,
              value: selectedTable,
              onValueChange: (value: string) => {
                selectedTable = value as ComparisonTable;
              },
            }}
          >
            {#if selectedTable === 'fills'}
              <FillComparisonTable fills={compared.fills} />
            {:else if compared.backtest.error_message === null}
              <EmptyText text="No logs" />
            {:else}
              <ScrollRegion label="Logs" fill>
                <pre class="log-text">{compared.backtest.error_message}</pre>
              </ScrollRegion>
            {/if}
          </Panel>
        {/if}
      {/snippet}
    </PanelSplit>
  {/if}
</Workbench>

<style>
  .empty-main {
    flex: 1;
    min-inline-size: 0;
  }

  .run-title {
    display: flex;
    align-items: baseline;
    gap: var(--cds-spacing-04);
    font-variant-numeric: tabular-nums;
  }

  /* One type size in the heading: Carbon links set their own size. */
  .run-title > :global(*) {
    font: inherit;
    letter-spacing: inherit;
  }

  .run-period {
    color: var(--cds-text-secondary);
  }

  .run-status {
    flex: none;
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    white-space: nowrap;
  }

  /* The metrics over the chart: the chart keeps at least 6rem, and the metrics take the rest up to their full height.
     In a low panel the metrics scroll in their own region (ComparedKeyMetrics) with a visible track. */
  .compare-area {
    display: grid;
    flex: 1;
    grid-template-rows: minmax(0, auto) minmax(var(--cds-spacing-12), 1fr);
    min-block-size: 0;
  }

  .metrics {
    min-block-size: 0;
  }

  /* The chart fills the rest of the panel body and follows its size (EquityDrawdownChart fill). */
  .chart {
    position: relative;
    min-block-size: 0;
    padding: var(--cds-spacing-03) var(--cds-spacing-05);
  }

  .log-text {
    margin: 0;
    padding: var(--cds-spacing-05);
    color: var(--cds-text-error);
    font-family: var(--cds-code-01-font-family);
    font-size: var(--cds-code-01-font-size);
    line-height: var(--cds-code-01-line-height);
    white-space: pre-wrap;
  }
</style>
