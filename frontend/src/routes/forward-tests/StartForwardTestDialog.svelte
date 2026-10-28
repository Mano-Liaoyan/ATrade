<!-- The "New forward test" dialog of the forward test workbench: the form that starts a forward test. The form combines
     strategy versions (strategy), the IB live bar periods (market_data), and the metrics of the latest finished
     backtest of the selected strategy version (backtest; docs/architecture/forward_test.md 12.16). The form id is
     START_FORWARD_TEST_FORM_ID: the command palette opens the dialog with it. -->
<script lang="ts">
  import { formatMaxDrawdown, formatPercent, formatUsd, listBacktests, type Backtest } from '#lib/backtest';
  import { Dialog, InlineNotification, Select, TextInput, type NotificationMessage, type SelectItem } from '#lib/foundation/carbon';
  import { formatBarPeriod } from '#lib/foundation/value_format';
  import { isLiveBarPeriod, readEndTimeUtc, startForwardTest, type ForwardTest } from '#lib/forward_test';
  import { BAR_PERIODS, DEFAULT_BAR_PERIOD, type BarPeriod } from '#lib/market_data';
  import {
    formatVersionLabel,
    listStrategies,
    readStrategy,
    type StrategyDetail,
    type StrategyListItem,
  } from '#lib/strategy';
  import { START_FORWARD_TEST_FORM_ID } from '../palette_commands';

  interface Props {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onStarted: (forwardTest: ForwardTest) => void;
  }

  const { open, onOpenChange, onStarted }: Props = $props();

  const liveBarPeriods = BAR_PERIODS.filter((period) => isLiveBarPeriod(period.value));
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
  let startError = $state<NotificationMessage | null>(null);
  let isStarting = $state(false);
  let form: HTMLFormElement | undefined = $state();

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

  // The metrics of the latest finished backtest of the selected strategy version (docs/architecture.md 12.1).
  const latestBacktest = $derived(
    backtests
      .filter((backtest) => String(backtest.strategy_version_id) === strategyVersionId && backtest.metrics !== null)
      .reduce<Backtest | null>((latest, backtest) => (latest === null || backtest.id > latest.id ? backtest : latest), null),
  );

  // Each open reads the choices again: a strategy or a backtest can be new.
  $effect(() => {
    if (!open) {
      return;
    }
    startError = null;
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

  async function selectStrategy(selectedId: string): Promise<void> {
    strategyId = selectedId;
    selectedStrategy = null;
    strategyVersionId = '';
    const result = await readStrategy(fetch, Number(selectedId));
    if (result.kind === 'failed') {
      startError = { kind: 'error', title: 'Strategy not read', subtitle: result.message };
      return;
    }
    selectedStrategy = result.value;
    const latestVersion = result.value.versions.at(-1);
    strategyVersionId = latestVersion === undefined ? '' : String(latestVersion.id);
  }

  async function submitForwardTest(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    // The dropdowns are not native selects, so the form checks them itself.
    if (strategyVersionId === '') {
      startError = { kind: 'error', title: 'Forward test not started', subtitle: 'Select a strategy version.' };
      return;
    }
    isStarting = true;
    startError = null;
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
      startError = { kind: 'error', title: 'Forward test not started', subtitle: result.message };
      return;
    }
    onStarted(result.forwardTest);
    onOpenChange(false);
  }
</script>

<Dialog
  {open}
  {onOpenChange}
  title="New forward test"
  size="md"
  primaryText={isStarting ? 'Starting…' : 'Start forward test'}
  busy={isStarting}
  onPrimary={() => form?.requestSubmit()}
>
  <form
    id={START_FORWARD_TEST_FORM_ID}
    class="forward-test-form"
    aria-label="Start a forward test"
    bind:this={form}
    onsubmit={submitForwardTest}
  >
    <Select
      label="Strategy"
      placeholder="Select a strategy"
      items={strategyItems}
      value={strategyId}
      onValueChange={(selectedId: string) => void selectStrategy(selectedId)}
    />
    <Select
      label="Strategy version"
      placeholder="Select a strategy first"
      items={versionItems}
      value={strategyVersionId}
      disabled={versionItems.length === 0}
      onValueChange={(versionId: string) => {
        strategyVersionId = versionId;
      }}
    />
    {#if strategyVersionId !== ''}
      <section class="form-note cds--form__helper-text" aria-label="Latest backtest result">
        {#if latestBacktest === null || latestBacktest.metrics === null}
          no backtest result
        {:else}
          Latest backtest #{latestBacktest.id} ({latestBacktest.symbol}, {formatBarPeriod(latestBacktest.bar_period)}): total
          return {formatPercent(latestBacktest.metrics.total_return_percent)}, max drawdown
          {formatMaxDrawdown(latestBacktest.metrics.max_drawdown_percent).text}, {latestBacktest.metrics.trade_count} trades,
          final equity {formatUsd(latestBacktest.metrics.final_equity_usd)} USD.
        {/if}
      </section>
    {/if}
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
  </form>
  {#if startError !== null}
    <InlineNotification {...startError} lowContrast onClose={() => (startError = null)} />
  {/if}
</Dialog>

<style>
  .forward-test-form {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--cds-spacing-05);
    margin-block-end: var(--cds-spacing-05);
  }

  .form-note {
    grid-column: 1 / -1;
    margin: 0;
  }
</style>
