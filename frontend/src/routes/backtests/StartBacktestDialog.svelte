<!-- The "New backtest" dialog of the backtest workbench: the form that starts a backtest. The form combines strategy
     versions (strategy), bar periods (market_data), watchlist instruments with saved bars (watchlist), and the paper
     capital (paper_trading). A backtest reads only saved bars, so the form offers only instruments with saved bars of
     the selected bar period (docs/architecture/backtest.md section 10.6). The form id is START_BACKTEST_FORM_ID: the
     command palette opens the dialog with it. With `strategyVersion`, each open selects that strategy version, for
     example the open version of the strategy page (Run backtest). -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { convertDateToUtcStart, startBacktest, type Backtest } from '#lib/backtest';
  import { Dialog, InlineNotification, Select, TextInput, type NotificationMessage } from '#lib/foundation/carbon';
  import { BAR_PERIODS, DEFAULT_BAR_PERIOD, type BarPeriod } from '#lib/market_data';
  import { readPaperCapital } from '#lib/paper_trading';
  import {
    formatVersionLabel,
    listStrategies,
    readStrategy,
    type StrategyDetail,
    type StrategyListItem,
  } from '#lib/strategy';
  import {
    describeSavedBars,
    findSavedBars,
    formatWatchlistInstrument,
    listWatchlist,
    selectInstrumentsWithSavedBars,
    type WatchlistInstrument,
  } from '#lib/watchlist';
  import { START_BACKTEST_FORM_ID } from '../palette_commands';

  interface Props {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onStarted: (backtest: Backtest) => void;
    strategyVersion?: { strategyId: number; versionId: number } | null;
  }

  const { open, onOpenChange, onStarted, strategyVersion = null }: Props = $props();

  let strategies: StrategyListItem[] = $state([]);
  let selectedStrategy = $state<StrategyDetail | null>(null);
  let strategyId = $state('');
  let strategyVersionId = $state('');
  let watchlistInstruments: WatchlistInstrument[] = $state([]);
  let watchlistMessage = $state('Loading the watchlist.');
  let watchlistInstrumentId = $state('');
  let barPeriod = $state<BarPeriod>(DEFAULT_BAR_PERIOD);
  let startDate = $state('');
  let endDate = $state('');
  let paperCapitalUsd = $state('');
  let startError = $state<NotificationMessage | null>(null);
  let isStarting = $state(false);
  let form: HTMLFormElement | undefined = $state();

  const barPeriodLabel = $derived(BAR_PERIODS.find((period) => period.value === barPeriod)?.label ?? barPeriod);
  const instrumentChoices = $derived(selectInstrumentsWithSavedBars(watchlistInstruments, barPeriod));
  const selectedInstrument = $derived(
    instrumentChoices.find((instrument) => String(instrument.id) === watchlistInstrumentId),
  );
  const selectedSavedBars = $derived(
    selectedInstrument === undefined ? undefined : findSavedBars(selectedInstrument, barPeriod),
  );
  const strategyItems = $derived(strategies.map((strategy) => ({ value: String(strategy.id), label: strategy.name })));
  const versionItems = $derived(
    selectedStrategy === null
      ? []
      : selectedStrategy.versions.map((version) => ({
          value: String(version.id),
          label: formatVersionLabel(selectedStrategy?.name ?? '', version.version_number),
        })),
  );
  const instrumentItems = $derived(
    instrumentChoices.map((instrument) => ({ value: String(instrument.id), label: formatWatchlistInstrument(instrument) })),
  );

  // Each open reads the choices again: a strategy or a watchlist instrument can be new.
  $effect(() => {
    if (!open) {
      return;
    }
    startError = null;
    if (strategyVersion !== null) {
      void selectStrategy(String(strategyVersion.strategyId), String(strategyVersion.versionId));
    }
    void listStrategies(fetch).then((result) => {
      if (result.kind === 'ok') {
        strategies = result.value;
      }
    });
    void listWatchlist(fetch).then((result) => {
      if (result.kind === 'ok') {
        watchlistInstruments = result.value;
        watchlistMessage = '';
      } else {
        watchlistMessage = result.message;
      }
    });
    if (paperCapitalUsd === '') {
      void readPaperCapital(fetch).then((paperCapital) => {
        paperCapitalUsd = paperCapital ?? '';
      });
    }
  });

  // A change of the bar period can remove the selected instrument from the choices.
  $effect(() => {
    if (watchlistInstrumentId !== '' && selectedInstrument === undefined) {
      watchlistInstrumentId = '';
    }
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

  async function submitBacktest(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    // The dropdowns are not native selects, so the form checks them itself.
    if (strategyVersionId === '' || selectedInstrument === undefined) {
      startError = { kind: 'error', title: 'Backtest not started', subtitle: 'Select a strategy version and an instrument.' };
      return;
    }
    isStarting = true;
    startError = null;
    const result = await startBacktest(fetch, {
      strategy_version_id: Number(strategyVersionId),
      symbol: selectedInstrument.symbol,
      exchange: selectedInstrument.exchange,
      currency: selectedInstrument.currency,
      bar_period: barPeriod,
      start_utc: convertDateToUtcStart(startDate),
      end_utc: convertDateToUtcStart(endDate),
      paper_capital_usd: paperCapitalUsd,
    });
    isStarting = false;
    if (result.kind === 'failed') {
      startError = { kind: 'error', title: 'Backtest not started', subtitle: result.message };
      return;
    }
    onStarted(result.value);
    onOpenChange(false);
  }
</script>

<Dialog
  {open}
  {onOpenChange}
  title="New backtest"
  size="md"
  primaryText={isStarting ? 'Starting…' : 'Start backtest'}
  busy={isStarting}
  onPrimary={() => form?.requestSubmit()}
>
  <form
    id={START_BACKTEST_FORM_ID}
    class="backtest-form"
    aria-label="Start a backtest"
    bind:this={form}
    onsubmit={submitBacktest}
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
    <Select
      label="Bar period"
      items={[...BAR_PERIODS]}
      value={barPeriod}
      onValueChange={(period: BarPeriod) => {
        barPeriod = period;
      }}
    />
    <Select
      label="Instrument"
      placeholder="Select an instrument"
      items={instrumentItems}
      value={watchlistInstrumentId}
      disabled={instrumentItems.length === 0}
      onValueChange={(instrumentId: string) => {
        watchlistInstrumentId = instrumentId;
      }}
    />
    <p class="form-note cds--form__helper-text" role="status" aria-label="Saved bars">
      {#if watchlistMessage !== ''}
        {watchlistMessage}
      {:else if instrumentChoices.length === 0}
        No watchlist instrument has saved {barPeriodLabel} bars. Add an instrument to the
        <a class="cds--link cds--link--sm" href={resolve('/')}>watchlist</a> and open its bar chart: the chart saves the bars.
      {:else if selectedSavedBars !== undefined}
        {describeSavedBars(selectedSavedBars)}
      {/if}
    </p>
    <TextInput label="Start date (UTC)" type="date" bind:value={startDate} required />
    <TextInput label="End date (UTC)" type="date" bind:value={endDate} required />
    <TextInput label="Paper capital (USD)" inputmode="decimal" class="number" bind:value={paperCapitalUsd} required />
  </form>
  {#if startError !== null}
    <InlineNotification {...startError} lowContrast onClose={() => (startError = null)} />
  {/if}
</Dialog>

<style>
  .backtest-form {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--cds-spacing-05);
    margin-block-end: var(--cds-spacing-05);
  }

  .backtest-form :global(input.number) {
    font-variant-numeric: tabular-nums;
    text-align: end;
  }

  .form-note {
    grid-column: 1 / -1;
    margin: 0;
  }
</style>
