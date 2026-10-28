<!-- Forward tests: the start form and the live list. The form combines strategy versions (strategy), bar periods
     (market_data), and the latest backtest metrics of the strategy version (backtest). -->
<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { formatMaxDrawdown, formatPercent, formatUsd, listBacktests, type Backtest } from '#lib/backtest';
  import { Button, InlineNotification, Select, TextInput, type NotificationMessage, type SelectItem } from '#lib/foundation/carbon';
  import { buildSocketUrl, LiveUpdatesNotification, openLiveSocket } from '#lib/foundation/live_socket';
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
  const startBlockId = 'forward-test-start-block';
  // The longest symbol, exchange, and currency that the API takes.
  const MAX_FIELD_LENGTH = 32;

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
  // The failed action and the reason from the backend.
  let failure = $state<NotificationMessage | null>(null);
  let isStarting = $state(false);

  const strategyItems = $derived<SelectItem<string>[]>(
    strategies.map((strategy) => ({ value: String(strategy.id), label: strategy.name })),
  );
  const versionItems = $derived<SelectItem<string>[]>(
    selectedStrategy === null
      ? []
      : selectedStrategy.versions.map((version) => ({
          value: String(version.id),
          label: formatVersionLabel(selectedStrategy?.name ?? '', version.version_number),
        })),
  );
  const startBlock = $derived(strategyVersionId === '' ? 'Select a strategy version to start a forward test.' : null);

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

  async function selectStrategy(selectedStrategyId: string): Promise<void> {
    strategyId = selectedStrategyId;
    selectedStrategy = null;
    strategyVersionId = '';
    if (strategyId === '') {
      return;
    }
    const result = await readStrategy(fetch, Number(strategyId));
    if (result.kind === 'failed') {
      failure = { kind: 'error', title: 'Strategy not read', subtitle: result.message };
      return;
    }
    selectedStrategy = result.value;
    const latestVersion = result.value.versions.at(-1);
    strategyVersionId = latestVersion === undefined ? '' : String(latestVersion.id);
  }

  async function submitForwardTest(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    isStarting = true;
    failure = null;
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
      failure = { kind: 'error', title: 'Forward test not started', subtitle: result.message };
      return;
    }
    forwardTests = [result.forwardTest, ...forwardTests.filter((item) => item.id !== result.forwardTest.id)];
  }

  // A normal backtest of the same strategy version, instrument, bar type, and period (docs/architecture 12.10).
  async function backtestSamePeriod(forwardTestId: number): Promise<void> {
    failure = null;
    const result = await startSamePeriodBacktest(fetch, forwardTestId);
    if (result.kind === 'failed') {
      failure = { kind: 'error', title: 'Backtest not started', subtitle: result.message };
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

<form id="start-forward-test" class="forward-test-form atrade-auto-grid" aria-label="Start a forward test" onsubmit={submitForwardTest}>
  <Select
    label="Strategy"
    placeholder="Select a strategy"
    items={strategyItems}
    value={strategyId}
    onValueChange={(selectedStrategyId: string) => void selectStrategy(selectedStrategyId)}
  />
  <Select
    label="Strategy version"
    placeholder="Select a strategy first"
    items={versionItems}
    value={strategyVersionId}
    disabled={selectedStrategy === null}
    onValueChange={(versionId: string) => {
      strategyVersionId = versionId;
    }}
  />
  <TextInput label="Symbol" autocomplete="off" required maxlength={MAX_FIELD_LENGTH} bind:value={symbol} />
  <TextInput label="Exchange" autocomplete="off" required maxlength={MAX_FIELD_LENGTH} bind:value={exchange} />
  <TextInput label="Currency" autocomplete="off" required maxlength={MAX_FIELD_LENGTH} bind:value={currency} />
  <Select
    label="Bar period"
    items={liveBarPeriods}
    value={barPeriod}
    onValueChange={(period: BarPeriod) => {
      barPeriod = period;
    }}
  />
  <TextInput label="End time (local, optional)" type="datetime-local" bind:value={endTimeLocal} />
  <div class="submit">
    <Button
      type="submit"
      disabled={startBlock !== null || isStarting}
      aria-describedby={startBlock === null ? undefined : startBlockId}>{isStarting ? 'Starting…' : 'Start forward test'}</Button
    >
    {#if startBlock !== null}
      <p id={startBlockId} class="message">{startBlock}</p>
    {/if}
  </div>
</form>

{#if strategyVersionId !== ''}
  <section class="latest-backtest" aria-label="Latest backtest result">
    {#if latestBacktest === null || latestBacktest.metrics === null}
      <p>no backtest result</p>
    {:else}
      <p>
        Latest backtest #{latestBacktest.id} ({latestBacktest.symbol}, {formatBarPeriod(latestBacktest.bar_period)}): total
        return {formatPercent(latestBacktest.metrics.total_return_percent)}, max drawdown
        {formatMaxDrawdown(latestBacktest.metrics.max_drawdown_percent).text}, {latestBacktest.metrics.trade_count} trades, final
        equity {formatUsd(latestBacktest.metrics.final_equity_usd)} USD.
      </p>
    {/if}
  </section>
{/if}

{#if failure !== null}
  <InlineNotification
    {...failure}
    lowContrast
    onClose={() => (failure = null)}
  />
{/if}

<h2>All forward tests</h2>
<LiveUpdatesNotification isConnected={isSocketConnected} />
<ForwardTestList {forwardTests} onBacktestSamePeriod={backtestSamePeriod} />

<style>
  .forward-test-form {
    align-items: end;
    margin-block-end: var(--cds-spacing-06);
  }

  .submit {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--cds-spacing-05);
    grid-column: 1 / -1;
  }

  .message,
  .latest-backtest p {
    margin: 0;
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    letter-spacing: var(--cds-body-compact-01-letter-spacing);
    color: var(--cds-text-secondary);
  }

  .latest-backtest {
    margin-block-end: var(--cds-spacing-06);
  }

  h2 {
    margin-block: var(--cds-spacing-07) var(--cds-spacing-05);
    font-size: var(--cds-heading-03-font-size);
    font-weight: var(--cds-heading-03-font-weight);
    line-height: var(--cds-heading-03-line-height);
  }
</style>
