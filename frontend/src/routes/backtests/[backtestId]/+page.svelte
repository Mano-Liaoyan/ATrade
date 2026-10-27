<!-- One backtest: its request and its result. The page reads the backtest again until its status is final. -->
<script lang="ts">
  import { InlineNotification } from '#lib/foundation/carbon';
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

<p class="page-back"><a class="cds--link" href={resolve('/backtests')}>All backtests</a></p>
<h1 class="page-heading">Backtest #{backtestId}</h1>

{#if errorMessage !== ''}
  <InlineNotification kind="error" title="Backtest not read" subtitle={errorMessage} lowContrast />
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

  .request {
    display: flex;
    flex-wrap: wrap;
    gap: var(--cds-spacing-05) var(--cds-spacing-07);
    margin: 0 0 var(--cds-spacing-06);
  }

  .request dt {
    font-size: var(--cds-label-01-font-size);
    line-height: var(--cds-label-01-line-height);
    letter-spacing: var(--cds-label-01-letter-spacing);
    color: var(--cds-text-secondary);
  }

  .request dd {
    margin: var(--cds-spacing-02) 0 0;
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    letter-spacing: var(--cds-body-compact-01-letter-spacing);
  }
</style>
