<!-- The metric card of the assistant side column (docs/architecture/assistant.md 25.12.1): the KeyMetricRow of a
     finished backtest, with a link to the backtest. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { KeyMetricRow, readBacktest, type BacktestDetail } from '#lib/backtest';

  const { backtestId }: { backtestId: number } = $props();

  let backtest = $state<BacktestDetail | null>(null);
  let message = $state('');

  $effect(() => {
    void readBacktest(fetch, backtestId).then((result) => {
      if (result.kind === 'ok') {
        backtest = result.value;
      } else {
        message = result.message;
      }
    });
  });

  const name = $derived(`Backtest #${String(backtestId)}`);
</script>

<div class="cds--tile assistant-card">
  <a class="cds--link" href={resolve('/backtests/[[backtestId]]', { backtestId: String(backtestId) })}>{name}</a>
  {#if backtest !== null}
    <KeyMetricRow
      label={`${name} metrics`}
      metrics={backtest.metrics}
      startCapitalUsd={backtest.paper_capital_usd}
    />
  {:else if message !== ''}
    <p class="card-message">{message}</p>
  {/if}
</div>

<style>
  .assistant-card {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-03);
    min-inline-size: 0;
    padding: var(--cds-spacing-04);
  }

  .card-message {
    color: var(--cds-text-error);
    font-size: var(--cds-label-01-font-size);
  }
</style>
