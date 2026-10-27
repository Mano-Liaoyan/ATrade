<!-- Comparison of two backtests of the same strategy: the code diff, the metric table, and both equity curves.
     The backend refuses backtests of different strategies, and the page shows its reason. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import { InlineNotification } from '#lib/foundation/carbon';
  import { compareBacktests, ComparisonView, type BacktestComparison } from '#lib/backtest';
  import { formatVersionLabel } from '#lib/strategy';

  const firstBacktestId = $derived(Number(page.params['backtestId']));
  const secondBacktestId = $derived(Number(page.params['otherBacktestId']));

  let comparison = $state<BacktestComparison | null>(null);
  let errorMessage = $state('');

  $effect(() => {
    let isActive = true;
    const firstId = firstBacktestId;
    const secondId = secondBacktestId;
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

  function makeRunLabel(backtest: BacktestComparison['first']): string {
    return `#${String(backtest.id)} ${formatVersionLabel(backtest.strategy_name, backtest.version_number)}`;
  }
</script>

<p class="page-back"><a class="cds--link" href={resolve('/backtests')}>All backtests</a></p>
<h1 class="page-heading">Compare backtests #{firstBacktestId} and #{secondBacktestId}</h1>

{#if errorMessage !== ''}
  <InlineNotification kind="error" title="Backtests not compared" subtitle={errorMessage} lowContrast />
{/if}

{#if comparison !== null}
  <ComparisonView
    first={{
      label: makeRunLabel(comparison.first),
      metrics: comparison.first.metrics,
      equityCurve: comparison.first.equity_curve,
    }}
    second={{
      label: makeRunLabel(comparison.second),
      metrics: comparison.second.metrics,
      equityCurve: comparison.second.equity_curve,
    }}
    code={{ firstCode: comparison.first.code, secondCode: comparison.second.code }}
  />
{/if}

<style>
  .page-back {
    margin-block: 0 var(--cds-spacing-05);
  }

  .page-heading {
    margin-block: 0 var(--cds-spacing-06);
    font-size: var(--cds-heading-04-font-size);
    font-weight: var(--cds-heading-04-font-weight);
    line-height: var(--cds-heading-04-line-height);
    letter-spacing: var(--cds-heading-04-letter-spacing);
  }
</style>
