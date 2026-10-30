<!-- Comparison of 2 backtests of the same strategy (docs/architecture section 9.5): a workbench (foundation/workbench,
     spec #99) with the structure of the backtest page. Left: the "Backtests" side column (BacktestList) with both
     compared rows marked. Center: the comparison panel (header line: the name, the strategy, and the instrument and bar period when both backtests
     have the same; then one key metric
     row for each backtest and both equity and drawdown curves on one time axis) over the Code difference panel.
     The backend refuses backtests of different strategies, and the page shows its reason. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import {
    compareBacktests,
    ComparedKeyMetrics,
    EquityDrawdownChart,
    isFinalStatus,
    listBacktests,
    readBacktestInstrument,
    type Backtest,
    type BacktestComparison,
    type BacktestInstrument,
    type ComparedTest,
    type DrawdownCurve,
  } from '#lib/backtest';
  import { Button, InlineNotification } from '#lib/foundation/carbon';
  import { CodeDiff } from '#lib/foundation/code_editor';
  import { startPolling } from '#lib/foundation/polling';
  import { formatBarPeriod } from '#lib/foundation/value_format';
  import { Panel, PanelSplit, SideColumn, Workbench, type PanelSpec } from '#lib/foundation/workbench';
  import { isSameInstrument } from '#lib/market_data';
  import { formatVersionLabel } from '#lib/strategy';
  import { createInstrumentHref } from '../../../../instrument_href';
  import BacktestList from '../../../BacktestList.svelte';

  const LIST_CHECK_INTERVAL_MILLISECONDS = 2000;
  // The panels of the backtest page. The chart panel has a higher minimum: the header line, the 2 metric rows (they
  // scroll when they do not fit), and the chart.
  const PANELS: PanelSpec[] = [
    { id: 'chart', minPixels: 256 },
    { id: 'tables', minPixels: 96, defaultPixels: 240, splitterLabel: 'Resize the chart and the tables' },
  ];
  const TABLE_TABS = [{ value: 'code', label: 'Code difference' }];

  const firstBacktestId = $derived(Number(page.params['backtestId']));
  const secondBacktestId = $derived(Number(page.params['otherBacktestId']));
  const title = $derived(`Compare backtests #${String(firstBacktestId)} and #${String(secondBacktestId)}`);

  let backtests: Backtest[] = $state([]);
  let listMessage = $state('');
  let comparison = $state<BacktestComparison | null>(null);
  let errorMessage = $state('');
  let isSameCodeOpen = $state(false);

  const comparedTests = $derived<ComparedTest[]>(
    comparison === null ? [] : [makeComparedTest(comparison.first), makeComparedTest(comparison.second)],
  );

  const firstName = $derived(comparedTests[0]?.name ?? '');
  const secondName = $derived(comparedTests[1]?.name ?? '');
  const comparedCurves = $derived<DrawdownCurve[]>(
    comparison === null
      ? []
      : [comparison.first, comparison.second].map((backtest, index) => ({
          name: comparedTests[index]?.name ?? '',
          points: backtest.equity_curve,
          startCapitalUsd: backtest.paper_capital_usd,
        })),
  );

  // The list reads again while a backtest in it is queued or running, like on the backtest page.
  $effect(() =>
    startPolling(
      () => listBacktests(fetch),
      (result) => {
        if (result.kind === 'failed') {
          listMessage = result.message;
          return true;
        }
        listMessage = '';
        backtests = result.value;
        return result.value.some((item) => !isFinalStatus(item.status));
      },
      LIST_CHECK_INTERVAL_MILLISECONDS,
      (message) => {
        listMessage = message;
      },
    ),
  );

  $effect(() => {
    let isActive = true;
    const firstId = firstBacktestId;
    const secondId = secondBacktestId;
    isSameCodeOpen = false;
    void compareBacktests(fetch, firstId, secondId).then((result) => {
      if (!isActive) {
        return;
      }
      if (result.kind === 'failed') {
        errorMessage = result.message;
        comparison = null;
        return;
      }
      errorMessage = '';
      comparison = result.value;
    });
    return () => {
      isActive = false;
    };
  });

  function makeComparedTest(backtest: BacktestComparison['first']): ComparedTest {
    return {
      name: `#${String(backtest.id)} ${formatVersionLabel(backtest.strategy_name, backtest.version_number)}`,
      href: resolve('/backtests/[[backtestId]]', { backtestId: String(backtest.id) }),
      metrics: backtest.metrics,
      startCapitalUsd: backtest.paper_capital_usd,
    };
  }

  // The instrument of both backtests, when they are single-instrument backtests of the same instrument.
  function findSharedInstrument(first: Backtest, second: Backtest): BacktestInstrument | undefined {
    const firstInstrument = readBacktestInstrument(first);
    const secondInstrument = readBacktestInstrument(second);
    if (firstInstrument === undefined || secondInstrument === undefined) {
      return undefined;
    }
    return isSameInstrument(firstInstrument, secondInstrument) ? firstInstrument : undefined;
  }
</script>

<Workbench>
  <SideColumn label="Backtests" side="start" width="36rem" storageKey="atrade.backtest-page.list-column">
    <BacktestList
      {backtests}
      errorMessage={listMessage}
      openBacktestId={null}
      comparedBacktestIds={[firstBacktestId, secondBacktestId]}
    />
  </SideColumn>

  {#if comparison === null}
    <div class="empty-main">
      {#if errorMessage !== ''}
        <InlineNotification kind="error" title="Backtests not compared" subtitle={errorMessage} lowContrast />
      {/if}
    </div>
  {:else}
    {@const compared = comparison}
    <PanelSplit storageKey="atrade.backtest-comparison-page.panel-split" panels={PANELS}>
      {#snippet panel(id, state)}
        {#if id === 'chart'}
          <Panel {...state} label={title}>
            {#snippet header()}
              <h1 class="run-title">
                <span>{title}</span>
                <a class="cds--link" href={resolve('/strategies/[strategyId]', { strategyId: String(compared.strategy_id) })}
                  >{compared.strategy_name}</a
                >
                <!-- The instrument and the bar period show when both backtests have the same one. -->
                {#snippet instrumentLink(sharedInstrument: BacktestInstrument | undefined)}
                  {#if sharedInstrument !== undefined}
                    <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- createInstrumentHref resolves the path. -->
                    <a class="cds--link" href={createInstrumentHref(sharedInstrument)}>{sharedInstrument.symbol}</a>
                  {/if}
                {/snippet}
                {@render instrumentLink(findSharedInstrument(compared.first, compared.second))}
                {#if compared.first.bar_period === compared.second.bar_period}
                  <span class="run-period">{formatBarPeriod(compared.first.bar_period)}</span>
                {/if}
              </h1>
            {/snippet}
            <div class="compare-area">
              <div class="metrics">
                <ComparedKeyMetrics tests={comparedTests} />
              </div>
              <div class="chart">
                <EquityDrawdownChart
                  curves={comparedCurves}
                  label="Equity and drawdown"
                  fill
                />
              </div>
            </div>
          </Panel>
        {:else}
          <Panel
            {...state}
            label="Comparison tables"
            tabs={{ label: 'Comparison tables', items: TABLE_TABS, value: 'code', onValueChange: () => {} }}
          >
            {#if compared.first.code === compared.second.code}
              <!-- Saving the same code again keeps the version, so the same code means the same strategy version. -->
              <InlineNotification
                kind="info"
                label="Code difference"
                title="Same strategy version: no code difference."
                lowContrast
              />
              <div class="same-code-action">
                <Button
                  kind="ghost"
                  size="sm"
                  aria-expanded={isSameCodeOpen}
                  onclick={() => {
                    isSameCodeOpen = !isSameCodeOpen;
                  }}
                >
                  {isSameCodeOpen ? 'Hide the code' : 'Show the code'}
                </Button>
              </div>
              {#if isSameCodeOpen}
                <div class="code">
                  <CodeDiff
                    firstCode={compared.first.code}
                    secondCode={compared.second.code}
                    firstLabel={firstName}
                    secondLabel={secondName}
                    collapseUnchanged={false}
                    fill
                  />
                </div>
              {/if}
            {:else}
              <div class="code">
                <CodeDiff
                  firstCode={compared.first.code}
                  secondCode={compared.second.code}
                  firstLabel={firstName}
                  secondLabel={secondName}
                  fill
                />
              </div>
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

  .same-code-action {
    flex: none;
  }

  /* The code difference fills the rest of the panel body and scrolls in its own region. */
  .code {
    flex: 1;
    min-block-size: 0;
  }
</style>
