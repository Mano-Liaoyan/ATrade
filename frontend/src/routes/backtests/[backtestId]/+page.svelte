<!-- One backtest: its request and its result. The page reads the backtest again until its status is final. -->
<script lang="ts">
  import { formatUtcTime } from '#lib/foundation/time_format';
  import { formatBarPeriod } from '#lib/foundation/value_format';
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import { BacktestResult, formatUsd, isFinalStatus, readBacktest, type BacktestDetail } from '#lib/backtest';
  import { formatVersionLabel } from '#lib/strategy';

  // A backtest of a few years of daily bars ends in seconds. One read each second is enough.
  const STATUS_CHECK_INTERVAL_MILLISECONDS = 1000;

  const backtestId = $derived(Number(page.params['backtestId']));

  let backtest = $state<BacktestDetail | null>(null);
  let errorMessage = $state('');

  $effect(() => {
    let isActive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const id = backtestId;

    async function readUntilFinal(): Promise<void> {
      const result = await readBacktest(fetch, id);
      if (!isActive) {
        return;
      }
      if (result.kind === 'failed') {
        errorMessage = result.message;
      } else {
        errorMessage = '';
        backtest = result.value;
        if (isFinalStatus(result.value.status)) {
          return;
        }
      }
      timer = setTimeout(() => void readUntilFinal(), STATUS_CHECK_INTERVAL_MILLISECONDS);
    }

    void readUntilFinal();
    return () => {
      isActive = false;
      clearTimeout(timer);
    };
  });
</script>

<p><a href={resolve('/backtests')}>All backtests</a></p>
<h1>Backtest #{backtestId}</h1>

{#if errorMessage !== ''}
  <p class="error" role="alert">{errorMessage}</p>
{/if}

{#if backtest !== null}
  <dl class="request" aria-label="Backtest request">
    <div>
      <dt>Strategy version</dt>
      <dd>{formatVersionLabel(backtest.strategy_name, backtest.version_number)}</dd>
    </div>
    <div>
      <dt>Instrument</dt>
      <dd>{backtest.symbol} / {backtest.exchange} / {backtest.currency}</dd>
    </div>
    <div>
      <dt>Bar period</dt>
      <dd>{formatBarPeriod(backtest.bar_period)}</dd>
    </div>
    <div>
      <dt>Time range</dt>
      <dd>{formatUtcTime(backtest.start_utc)} to {formatUtcTime(backtest.end_utc)}</dd>
    </div>
    <div>
      <dt>Paper capital (USD)</dt>
      <dd>{formatUsd(backtest.paper_capital_usd)}</dd>
    </div>
  </dl>

  <BacktestResult {backtest} />
{/if}

<style>
  .error {
    color: var(--color-warning);
  }

  .request {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem 1.5rem;
    margin: 0 0 1rem;
  }

  .request dt {
    color: var(--color-muted);
    font-size: 0.875rem;
  }

  .request dd {
    margin: 0;
  }
</style>
