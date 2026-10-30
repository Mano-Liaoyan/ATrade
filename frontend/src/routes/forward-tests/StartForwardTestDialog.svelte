<!-- The "New forward test" dialog of the forward test workbench: the form that starts a forward test. The form combines
     strategy versions (strategy), the IB live bar periods (market_data), and the metrics of the latest finished
     backtest of the selected strategy version (backtest; docs/architecture/forward_test.md 12.16), and the allocated
     capital with the unallocated amount of the paper account (12.18; paper_trading gives the account check). The form id is
     START_FORWARD_TEST_FORM_ID: the command palette opens the dialog with it. With `strategyVersion`, each open selects
     that strategy version, for example the open version of the strategy page (Start forward test). -->
<script lang="ts">
  import { formatMaxDrawdown, formatPercent, formatUsd, listBacktests, type Backtest } from '#lib/backtest';
  import {
    Dialog,
    InlineNotification,
    Select,
    StatusIndicator,
    TextInput,
    type NotificationMessage,
    type SelectItem,
  } from '#lib/foundation/carbon';
  import { buildSocketUrl, openLiveSocket } from '#lib/foundation/live_socket';
  import { formatBarPeriod } from '#lib/foundation/value_format';
  import {
    describeUnallocated,
    findCapitalBlockReason,
    isLiveBarPeriod,
    readEndTimeUtc,
    readForwardTestCapital,
    startForwardTest,
    type ForwardTest,
    type ForwardTestCapital,
  } from '#lib/forward_test';
  import { BAR_PERIODS, DEFAULT_BAR_PERIOD, type BarPeriod } from '#lib/market_data';
  import {
    describePaperAccountCheck,
    describePaperAccountTag,
    PAPER_TRADING_SOCKET_PATH,
    readPaperAccountMessage,
    type PaperAccountCheck,
  } from '#lib/paper_trading';
  import {
    formatVersionLabel,
    listStrategies,
    readStrategy,
    type StrategyDetail,
    type StrategyListItem,
    type StrategyVersionKey,
  } from '#lib/strategy';
  import { START_FORWARD_TEST_FORM_ID } from '../palette_commands';

  interface Props {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onStarted: (forwardTest: ForwardTest) => void;
    strategyVersion?: StrategyVersionKey | null;
  }

  const { open, onOpenChange, onStarted, strategyVersion = null }: Props = $props();
  const uid = $props.id();
  const capitalInputId = `forward-test-capital-${uid}`;
  const capitalReasonId = `forward-test-capital-reason-${uid}`;

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
  let allocatedCapitalUsd = $state('');
  // 'reading' until GET /api/forward-tests/capital answers, null when the backend did not answer.
  let capital = $state<ForwardTestCapital | null | 'reading'>('reading');
  let paperAccountCheck = $state<PaperAccountCheck | null>(null);
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

  const unallocatedUsd = $derived(capital === 'reading' || capital === null ? null : capital.unallocated_usd);
  const capitalBlockReason = $derived(
    findCapitalBlockReason(allocatedCapitalUsd, unallocatedUsd, describeUnallocatedUnavailable()),
  );

  // Without an unallocated amount the backend refuses the start (forward_test.md 12.13). The dialog says why.
  function describeUnallocatedUnavailable(): string {
    if (capital === 'reading') {
      return 'Reading the unallocated amount.';
    }
    if (capital === null) {
      return 'Backend not reachable. The unallocated amount is not available.';
    }
    if (paperAccountCheck?.status === 'passed') {
      return 'The paper account has no NetLiquidation value in USD.';
    }
    return paperAccountCheck === null
      ? describePaperAccountTag(null)
      : describePaperAccountCheck(paperAccountCheck).title;
  }

  function refreshCapital(): void {
    void readForwardTestCapital(fetch).then((value) => {
      capital = value;
    });
  }

  // The reason of the paper account check, while the dialog is open.
  $effect(() => {
    if (!open) {
      return;
    }
    return openLiveSocket({
      url: buildSocketUrl(PAPER_TRADING_SOCKET_PATH, window.location),
      onMessage: (message) => {
        const accountMessage = readPaperAccountMessage(message);
        if (accountMessage !== null) {
          paperAccountCheck = accountMessage.check;
        }
      },
      onConnectionChange: () => undefined,
    });
  });

  // Each open reads the choices and the unallocated amount again: a strategy, a backtest, or a forward test can be new.
  $effect(() => {
    if (!open) {
      return;
    }
    startError = null;
    capital = 'reading';
    refreshCapital();
    if (strategyVersion !== null) {
      void selectStrategy(String(strategyVersion.strategyId), String(strategyVersion.versionId));
    }
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

  // Without a version id, the latest version of the strategy is selected.
  async function selectStrategy(selectedId: string, versionId: string | null = null): Promise<void> {
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
    strategyVersionId = versionId ?? (latestVersion === undefined ? '' : String(latestVersion.id));
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
      allocated_capital_usd: allocatedCapitalUsd.trim(),
      end_time_utc: readEndTimeUtc(endTimeLocal),
    });
    isStarting = false;
    if (result.kind === 'failed') {
      startError = { kind: 'error', title: 'Forward test not started', subtitle: result.message };
      // A refusal can come from a changed unallocated amount: another forward test started.
      refreshCapital();
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
  primaryDisabled={capitalBlockReason !== null}
  primaryDescribedBy={unallocatedUsd === null ? capitalReasonId : `${capitalInputId}-error`}
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
    <TextInput
      id={capitalInputId}
      label="Capital (USD)"
      inputmode="decimal"
      class="number"
      bind:value={allocatedCapitalUsd}
      required
      noteText={unallocatedUsd === null ? null : describeUnallocated(unallocatedUsd)}
      invalidText={unallocatedUsd === null ? null : capitalBlockReason}
    />
    <TextInput label="End time (local, optional)" type="datetime-local" bind:value={endTimeLocal} />
    {#if unallocatedUsd === null && capitalBlockReason !== null}
      <p id={capitalReasonId} class="form-note">
        <StatusIndicator kind={capital === 'reading' ? 'in-progress' : 'warning'} label={capitalBlockReason} />
      </p>
    {/if}
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

  /* The amounts of the helper text and the invalid message line up as numbers. */
  .forward-test-form :global(.cds--form__helper-text),
  .forward-test-form :global(.cds--form-requirement) {
    font-variant-numeric: tabular-nums;
  }
</style>
