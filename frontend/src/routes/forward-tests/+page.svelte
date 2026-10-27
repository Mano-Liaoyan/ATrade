<!-- Forward tests: the start form and the live list. The form combines strategy versions (strategy), bar periods
     (market_data), and the latest backtest metrics of the strategy version (backtest). -->
<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { formatPercent, formatUsd, listBacktests, type Backtest } from '#lib/backtest';
  import { buildSocketUrl, openLiveSocket } from '#lib/foundation/live_socket';
  import { formatBarPeriod } from '#lib/foundation/value_format';
  import {
    FORWARD_TESTS_SOCKET_PATH,
    ForwardTestList,
    isLiveBarPeriod,
    readEndTimeUtc,
    readForwardTestsMessage,
    startForwardTest,
    startSamePeriodBacktest,
    type ForwardTest,
  } from '#lib/forward_test';
  import { BAR_PERIODS, DEFAULT_BAR_PERIOD, type BarPeriod } from '#lib/market_data';
  import {
    formatVersionLabel,
    listStrategies,
    readStrategy,
    type StrategyDetail,
    type StrategyListItem,
  } from '#lib/strategy';

  const liveBarPeriods = BAR_PERIODS.filter((period) => isLiveBarPeriod(period.value));

  let strategies: StrategyListItem[] = $state([]);
  let selectedStrategy = $state<StrategyDetail | null>(null);
  let strategyId = $state('');
  let strategyVersionId = $state('');
  let symbol = $state('');
  let exchange = $state('');
  let currency = $state('USD');
  let barPeriod = $state<BarPeriod>(DEFAULT_BAR_PERIOD);
  // The value of the datetime-local input: a local time, or '' for no end time.
  let endTimeLocal = $state('');
  let backtests: Backtest[] = $state([]);
  let forwardTests: ForwardTest[] = $state([]);
  let isSocketConnected = $state(false);
  let errorMessage = $state('');
  let isStarting = $state(false);

  // The metrics of the latest finished backtest of the selected strategy version (docs/architecture.md 12.1).
  const latestBacktest = $derived(
    backtests
      .filter((backtest) => String(backtest.strategy_version_id) === strategyVersionId && backtest.metrics !== null)
      .reduce<Backtest | null>((latest, backtest) => (latest === null || backtest.id > latest.id ? backtest : latest), null),
  );

  $effect(() => {
    void listStrategies(fetch).then((result) => {
      if (result.kind === 'ok') {
        strategies = result.value;
      }
    });
    void listBacktests(fetch).then((result) => {
      if (result.kind === 'ok') {
        backtests = result.value;
      }
    });
  });

  $effect(() => {
    return openLiveSocket({
      url: buildSocketUrl(FORWARD_TESTS_SOCKET_PATH, window.location),
      onMessage: (message) => {
        const forwardTestsMessage = readForwardTestsMessage(message);
        if (forwardTestsMessage !== null) {
          forwardTests = forwardTestsMessage;
        }
      },
      onConnectionChange: (isConnected) => {
        isSocketConnected = isConnected;
      },
    });
  });

  async function selectStrategy(): Promise<void> {
    selectedStrategy = null;
    strategyVersionId = '';
    if (strategyId === '') {
      return;
    }
    const result = await readStrategy(fetch, Number(strategyId));
    if (result.kind === 'failed') {
      errorMessage = result.message;
      return;
    }
    selectedStrategy = result.value;
    const latestVersion = result.value.versions.at(-1);
    strategyVersionId = latestVersion === undefined ? '' : String(latestVersion.id);
  }

  async function submitForwardTest(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    isStarting = true;
    errorMessage = '';
    const result = await startForwardTest(fetch, {
      strategy_version_id: Number(strategyVersionId),
      symbol: symbol.trim().toUpperCase(),
      exchange: exchange.trim().toUpperCase(),
      currency: currency.trim().toUpperCase(),
      bar_period: barPeriod,
      end_time_utc: readEndTimeUtc(endTimeLocal),
    });
    isStarting = false;
    if (result.kind === 'failed') {
      errorMessage = result.message;
      return;
    }
    forwardTests = [result.forwardTest, ...forwardTests.filter((item) => item.id !== result.forwardTest.id)];
  }

  // A normal backtest of the same strategy version, instrument, bar type, and period (docs/architecture 12.10).
  async function backtestSamePeriod(forwardTestId: number): Promise<void> {
    errorMessage = '';
    const result = await startSamePeriodBacktest(fetch, forwardTestId);
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

<h1>Forward tests</h1>
<p class="explanation">
  A forward test runs a strategy version on live IB bars and sends orders to the paper account. It starts now and runs
  until you stop it, or until its end time. A stop cancels its open orders. Its positions stay open.
</p>

<form id="start-forward-test" class="forward-test-form" aria-label="Start a forward test" onsubmit={submitForwardTest}>
  <!-- The select is outside its label: the name of a select inside a label would also hold the selected option. -->
  <div class="field">
    <label for="forward-test-strategy">Strategy</label>
    <select id="forward-test-strategy" bind:value={strategyId} onchange={selectStrategy} required>
      <option value="">Select a strategy</option>
      {#each strategies as strategy (strategy.id)}
        <option value={String(strategy.id)}>{strategy.name}</option>
      {/each}
    </select>
  </div>
  <div class="field">
    <label for="forward-test-strategy-version">Strategy version</label>
    <select id="forward-test-strategy-version" bind:value={strategyVersionId} required>
      {#if selectedStrategy !== null}
        {#each selectedStrategy.versions as version (version.id)}
          <option value={String(version.id)}>{formatVersionLabel(selectedStrategy.name, version.version_number)}</option>
        {/each}
      {/if}
    </select>
  </div>
  <label>
    Symbol
    <input bind:value={symbol} required maxlength="32" />
  </label>
  <label>
    Exchange
    <input bind:value={exchange} required maxlength="32" />
  </label>
  <label>
    Currency
    <input bind:value={currency} required maxlength="32" />
  </label>
  <div class="field">
    <label for="forward-test-bar-period">Bar period</label>
    <select id="forward-test-bar-period" bind:value={barPeriod}>
      {#each liveBarPeriods as period (period.value)}
        <option value={period.value}>{period.label}</option>
      {/each}
    </select>
  </div>
  <label>
    End time (local, optional)
    <input type="datetime-local" bind:value={endTimeLocal} />
  </label>
  <button type="submit" disabled={isStarting}>Start forward test</button>
</form>

<section class="latest-backtest" aria-label="Latest backtest result">
  {#if strategyVersionId === ''}
    <p>Select a strategy version to see its latest backtest result.</p>
  {:else if latestBacktest === null || latestBacktest.metrics === null}
    <p>no backtest result</p>
  {:else}
    <p>
      Latest backtest #{latestBacktest.id} ({latestBacktest.symbol}, {formatBarPeriod(latestBacktest.bar_period)}): total return
      {formatPercent(latestBacktest.metrics.total_return_percent)}, max drawdown
      {formatPercent(latestBacktest.metrics.max_drawdown_percent)}, {latestBacktest.metrics.trade_count} trades, final
      equity {formatUsd(latestBacktest.metrics.final_equity_usd)} USD.
    </p>
  {/if}
</section>

{#if errorMessage !== ''}
  <p class="error" role="alert">{errorMessage}</p>
{/if}

<h2>All forward tests</h2>
{#if !isSocketConnected}
  <p class="live-status">Live updates paused. ATrade connects again.</p>
{/if}
<ForwardTestList {forwardTests} onBacktestSamePeriod={backtestSamePeriod} />

<style>
  .explanation {
    max-inline-size: 50rem;
  }

  .forward-test-form {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(12rem, 1fr));
    align-items: end;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }

  .forward-test-form label,
  .forward-test-form .field {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .latest-backtest {
    margin-bottom: 1rem;
    color: var(--color-muted);
  }

  .error,
  .live-status {
    color: var(--color-warning);
  }
</style>
