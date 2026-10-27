<!-- One forward test (docs/architecture/forward_test.md section 12.16): its setup, its state, its interruptions, its
     records (metrics, equity curve, fills), and a link to the comparison with each backtest of the same period.
     The page reads the forward test again every 2 seconds. -->
<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import { describeBacktestStatus, EquityChart, formatPercent, formatUsd, type TimeInterval } from '#lib/backtest';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatUtcTime } from '#lib/foundation/time_format';
  import { formatAmount, formatBarPeriod } from '#lib/foundation/value_format';
  import {
    canBacktestSamePeriod,
    describeForwardTestStatus,
    describeInterruptionReason,
    formatLocalTime,
    ForwardTestFillTable,
    readForwardTestDetail,
    showsCrashCount,
    startSamePeriodBacktest,
    type ForwardTestDetail,
  } from '#lib/forward_test';
  import { formatVersionLabel } from '#lib/strategy';

  const READ_INTERVAL_MILLISECONDS = 2000;

  const forwardTestId = $derived(Number(page.params['forwardTestId']));

  let detail = $state<ForwardTestDetail | null>(null);
  let errorMessage = $state('');
  let isStartingBacktest = $state(false);

  // An interruption that still lasts is grey on the chart up to now.
  const chartInterruptions = $derived<TimeInterval[]>(
    (detail?.forward_test.interruptions ?? []).map((interruption) => ({
      start_utc: interruption.started_at_utc,
      end_utc: interruption.ended_at_utc ?? new Date().toISOString(),
    })),
  );

  $effect(() => {
    let isActive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    // A new value only after a change: then the equity chart keeps its zoom while nothing changes.
    let lastDetailText = '';
    const currentForwardTestId = forwardTestId;

    async function readDetail(): Promise<void> {
      const result = await readForwardTestDetail(fetch, currentForwardTestId);
      if (!isActive) {
        return;
      }
      if (result.kind === 'failed') {
        errorMessage = result.message;
      } else {
        errorMessage = '';
        const detailText = JSON.stringify(result.value);
        if (detailText !== lastDetailText) {
          lastDetailText = detailText;
          detail = result.value;
        }
      }
      timer = setTimeout(() => void readDetail(), READ_INTERVAL_MILLISECONDS);
    }

    void readDetail();
    return () => {
      isActive = false;
      clearTimeout(timer);
    };
  });

  async function backtestSamePeriod(): Promise<void> {
    isStartingBacktest = true;
    errorMessage = '';
    const result = await startSamePeriodBacktest(fetch, forwardTestId);
    isStartingBacktest = false;
    if (result.kind === 'failed') {
      errorMessage = result.message;
      return;
    }
    await goto(
      resolve('/forward-tests/[forwardTestId]/comparison/[backtestId]', {
        forwardTestId: String(forwardTestId),
        backtestId: String(result.backtestId),
      }),
    );
  }
</script>

<p><a href={resolve('/forward-tests')}>All forward tests</a></p>
<h1>Forward test #{forwardTestId}</h1>

{#if errorMessage !== ''}
  <p class="error" role="alert">{errorMessage}</p>
{/if}

{#if detail !== null}
  {@const forwardTest = detail.forward_test}
  <dl class="setup" aria-label="Forward test">
    <div>
      <dt>Strategy version</dt>
      <dd>{formatVersionLabel(forwardTest.strategy_name, forwardTest.version_number)}</dd>
    </div>
    <div>
      <dt>Instrument</dt>
      <dd>{forwardTest.symbol} / {forwardTest.exchange} / {forwardTest.currency}</dd>
    </div>
    <div>
      <dt>Bar period</dt>
      <dd>{formatBarPeriod(forwardTest.bar_period)}</dd>
    </div>
    <div>
      <dt>Status</dt>
      <dd>
        {describeForwardTestStatus(forwardTest.status)}
        {#if showsCrashCount(forwardTest)}
          <span class="note">Crashes in a row: {forwardTest.crash_count} of 3</span>
        {/if}
        {#if forwardTest.error_message !== null}
          <span class="note error">{forwardTest.error_message}</span>
        {/if}
      </dd>
    </div>
    <div>
      <dt>Client ID</dt>
      <dd>{forwardTest.client_id ?? 'None'}</dd>
    </div>
    <div>
      <dt>Start balance (USD)</dt>
      <dd>{forwardTest.start_balance_usd === null ? 'Not read yet' : formatAmount(forwardTest.start_balance_usd)}</dd>
    </div>
    <div>
      <dt>Started</dt>
      <dd>{formatUtcTime(forwardTest.created_at_utc)}</dd>
    </div>
    <div>
      <dt>Stopped</dt>
      <dd>{forwardTest.stopped_at_utc === null ? 'Not stopped' : formatUtcTime(forwardTest.stopped_at_utc)}</dd>
    </div>
    <div>
      <dt>End time (local)</dt>
      <dd>{forwardTest.end_time_utc === null ? 'None' : formatLocalTime(forwardTest.end_time_utc)}</dd>
    </div>
  </dl>

  <h2>Interruptions</h2>
  {#if forwardTest.interruptions.length === 0}
    <p>No interruption.</p>
  {:else}
    <ScrollRegion label="Interruptions" maxHeight="min(14rem, 35vh)">
      <table class="detail-table">
        <thead>
          <tr>
            <th scope="col">Reason</th>
            <th scope="col">From</th>
            <th scope="col">To</th>
          </tr>
        </thead>
        <tbody>
          {#each forwardTest.interruptions as interruption (interruption.started_at_utc)}
            <tr>
              <th scope="row">{describeInterruptionReason(interruption.reason)}</th>
              <td>{formatUtcTime(interruption.started_at_utc)}</td>
              <td>{interruption.ended_at_utc === null ? 'Still lasts' : formatUtcTime(interruption.ended_at_utc)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </ScrollRegion>
  {/if}

  <h2>Result</h2>
  {#if detail.metrics === null}
    <p>No result yet. The result starts at the start balance.</p>
  {:else}
    <dl class="metrics" aria-label="Forward test metrics">
      <div>
        <dt>Final equity (USD)</dt>
        <dd>{formatUsd(detail.metrics.final_equity_usd)}</dd>
      </div>
      <div>
        <dt>Total return</dt>
        <dd>{formatPercent(detail.metrics.total_return_percent)}</dd>
      </div>
      <div>
        <dt>Max drawdown</dt>
        <dd>{formatPercent(detail.metrics.max_drawdown_percent)}</dd>
      </div>
      <div>
        <dt>Trades</dt>
        <dd>{detail.metrics.trade_count}</dd>
      </div>
    </dl>
  {/if}
  {#if detail.equity_curve.length === 0}
    <p>No equity point yet. The forward test records one at the end of each bar.</p>
  {:else}
    <EquityChart
      curves={[{ name: 'Equity', points: detail.equity_curve }]}
      label="Forward test equity curve"
      interruptions={chartInterruptions}
    />
  {/if}

  <h2>Fills</h2>
  <ForwardTestFillTable fills={detail.fills} />

  <h2>Backtests of the same period</h2>
  {#if detail.same_period_backtests.length === 0}
    <p>No backtest of the same period yet.</p>
  {:else}
    <ul class="backtest-links" aria-label="Backtests of the same period">
      {#each detail.same_period_backtests as backtest (backtest.id)}
        <li>
          <a
            href={resolve('/forward-tests/[forwardTestId]/comparison/[backtestId]', {
              forwardTestId: String(forwardTest.id),
              backtestId: String(backtest.id),
            })}>Compare with backtest #{backtest.id}</a
          >
          ({describeBacktestStatus(backtest.status)}, {formatUtcTime(backtest.start_utc)} to
          {formatUtcTime(backtest.end_utc)})
        </li>
      {/each}
    </ul>
  {/if}
  {#if canBacktestSamePeriod(forwardTest)}
    <button type="button" disabled={isStartingBacktest} onclick={backtestSamePeriod}>Backtest the same period</button>
  {/if}
{/if}

<style>
  .error {
    color: var(--color-warning);
  }

  .note {
    display: block;
    font-size: 0.875rem;
  }

  h2 {
    margin: 1rem 0 0.5rem;
    font-size: 1.125rem;
  }

  p {
    margin: 0 0 0.5rem;
  }

  .setup,
  .metrics {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
    gap: 0.5rem 1rem;
    margin: 0;
  }

  .setup dt,
  .metrics dt {
    color: var(--color-muted);
    font-size: 0.875rem;
  }

  .setup dd,
  .metrics dd {
    margin: 0;
    overflow-wrap: anywhere;
  }

  .detail-table {
    border-collapse: collapse;
    inline-size: 100%;
    font-size: 0.875rem;
  }

  .detail-table th,
  .detail-table td {
    padding: 0.375rem 0.75rem;
    border-bottom: 1px solid var(--color-border);
    text-align: start;
  }

  .detail-table thead th {
    position: sticky;
    inset-block-start: 0;
    background: var(--color-surface);
  }

  .backtest-links {
    margin: 0 0 0.75rem;
    padding-inline-start: 1.25rem;
  }
</style>
