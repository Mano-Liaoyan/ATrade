<!-- A forward test compared with a backtest of the same period (docs/architecture/forward_test.md section 12.10): the
     comparison view of the backtests (metric table, both equity curves, interruptions in grey) and the fill table.
     The page reads the comparison again every 2 seconds until the backtest has its final status. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import { ComparisonView, describeBacktestStatus, isFinalStatus } from '#lib/backtest';
  import { InlineNotification } from '#lib/foundation/carbon';
  import { FillComparisonTable, readForwardTestComparison, type ForwardTestComparison } from '#lib/forward_test';
  import { formatVersionLabel } from '#lib/strategy';

  const READ_INTERVAL_MILLISECONDS = 2000;

  const forwardTestId = $derived(Number(page.params['forwardTestId']));
  const backtestId = $derived(Number(page.params['backtestId']));

  let comparison = $state<ForwardTestComparison | null>(null);
  let errorMessage = $state('');

  $effect(() => {
    let isActive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const currentForwardTestId = forwardTestId;
    const currentBacktestId = backtestId;

    async function readComparison(): Promise<void> {
      const result = await readForwardTestComparison(fetch, currentForwardTestId, currentBacktestId);
      if (!isActive) {
        return;
      }
      if (result.kind === 'failed') {
        errorMessage = result.message;
        return;
      }
      errorMessage = '';
      comparison = result.value;
      if (!isFinalStatus(result.value.backtest.status)) {
        timer = setTimeout(() => void readComparison(), READ_INTERVAL_MILLISECONDS);
      }
    }

    void readComparison();
    return () => {
      isActive = false;
      clearTimeout(timer);
    };
  });

  function makeForwardTestLabel(value: ForwardTestComparison): string {
    const forwardTest = value.forward_test;
    return `Forward test #${String(forwardTest.id)} ${formatVersionLabel(forwardTest.strategy_name, forwardTest.version_number)}`;
  }
</script>

<p class="back-link"><a class="cds--link" href={resolve('/forward-tests/[[forwardTestId]]', {})}>All forward tests</a></p>
<h1>Compare forward test #{forwardTestId} with backtest #{backtestId}</h1>

{#if errorMessage !== ''}
  <InlineNotification kind="error" title={errorMessage} lowContrast />
{/if}

{#if comparison !== null}
  <p class="backtest-status" role="status" aria-label="Backtest status">
    Backtest #{comparison.backtest.id}: {describeBacktestStatus(comparison.backtest.status)}.
    {#if comparison.backtest.error_message !== null}
      {comparison.backtest.error_message}
    {/if}
  </p>
  <ComparisonView
    first={{
      label: makeForwardTestLabel(comparison),
      metrics: comparison.forward_test_metrics,
      equityCurve: comparison.forward_test_equity_curve,
    }}
    second={{
      label: `Backtest #${String(comparison.backtest.id)}`,
      metrics: comparison.backtest.metrics,
      equityCurve: comparison.backtest_equity_curve,
    }}
    interruptions={comparison.interruptions}
  />
  <h2>Fills</h2>
  <FillComparisonTable fills={comparison.fills} />
{/if}

<style>
  .back-link {
    margin-block: 0 var(--cds-spacing-05);
  }

  .backtest-status {
    margin-block: 0 var(--cds-spacing-05);
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    color: var(--cds-text-secondary);
  }

  h2 {
    margin-block: var(--cds-spacing-07) var(--cds-spacing-05);
    font-size: var(--cds-heading-03-font-size);
    font-weight: var(--cds-heading-03-font-weight);
    line-height: var(--cds-heading-03-line-height);
  }
</style>
