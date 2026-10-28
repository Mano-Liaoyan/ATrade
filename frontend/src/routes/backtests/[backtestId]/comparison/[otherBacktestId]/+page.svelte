<!-- Comparison of 2 backtests of the same strategy (docs/architecture section 9.5): a workbench (foundation/workbench,
     spec #99) with the structure of the backtest page. Left: the "Backtests" side column (BacktestList) with both
     compared rows marked. Center: the comparison panel (header line: the name and the strategy; then one key metric
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
    type Backtest,
    type BacktestComparison,
    type ComparedTest,
    type DrawdownCurve,
  } from '#lib/backtest';
  import { Button, InlineNotification } from '#lib/foundation/carbon';
  import { CodeDiff } from '#lib/foundation/code_editor';
  import { Panel, PanelSplit, SideColumn, Workbench, type PanelSpec } from '#lib/foundation/workbench';
  import { formatVersionLabel } from '#lib/strategy';
  import BacktestList from '../../../BacktestList.svelte';

  const LIST_CHECK_INTERVAL_MILLISECONDS = 2000;
  // The same panels and sizes as the backtest page.
  const PANELS: PanelSpec[] = [
    { id: 'chart', minPixels: 160 },
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
  $effect(() => {
    let isActive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function readList(): Promise<void> {
      const result = await listBacktests(fetch);
      if (!isActive) {
        return;
      }
      if (result.kind === 'failed') {
        listMessage = result.message;
        return;
      }
      listMessage = '';
      backtests = result.value;
      if (result.value.some((item) => !isFinalStatus(item.status))) {
        timer = setTimeout(() => void readList(), LIST_CHECK_INTERVAL_MILLISECONDS);
      }
    }

    void readList();
    return () => {
      isActive = false;
      clearTimeout(timer);
    };
  });

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
      trades: backtest.trades,
    };
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
              </h1>
            {/snippet}
            <ComparedKeyMetrics tests={comparedTests} />
            <div class="chart">
              <EquityDrawdownChart
                curves={comparedCurves}
                label="Equity and drawdown"
                fill
              />
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

  /* The chart fills the rest of the panel body and follows its size (EquityDrawdownChart fill). */
  .chart {
    position: relative;
    flex: 1;
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
