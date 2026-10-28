<!-- PROTOTYPE (#99), throwaway: the Run backtest dialog of the strategy workbench. It has the fields of the PR #98
     backtest form (bar period, watchlist instrument with saved bars, date range, paper capital). The strategy version
     is the open version of the workbench. -->
<script lang="ts">
  import { convertDateToUtcStart, startBacktest, type Backtest } from '#lib/backtest';
  import { Dialog, InlineNotification, Select, TextInput } from '#lib/foundation/carbon';
  import { BAR_PERIODS, DEFAULT_BAR_PERIOD, type BarPeriod } from '#lib/market_data';
  import { readPaperCapital } from '#lib/paper_trading';
  import {
    describeSavedBars,
    findSavedBars,
    formatWatchlistInstrument,
    listWatchlist,
    selectInstrumentsWithSavedBars,
    type WatchlistInstrument,
  } from '#lib/watchlist';

  interface Props {
    open: boolean;
    title: string;
    strategyVersionId: number | null;
    onOpenChange: (open: boolean) => void;
    onStarted: (backtest: Backtest) => void;
  }

  const { open, title, strategyVersionId, onOpenChange, onStarted }: Props = $props();

  let watchlistInstruments: WatchlistInstrument[] = $state([]);
  let watchlistMessage = $state('Loading the watchlist.');
  let watchlistInstrumentId = $state('');
  let barPeriod = $state<BarPeriod>(DEFAULT_BAR_PERIOD);
  let startDate = $state('');
  let endDate = $state('');
  let paperCapitalUsd = $state('');
  let startError = $state('');
  let isStarting = $state(false);

  const instrumentChoices = $derived(selectInstrumentsWithSavedBars(watchlistInstruments, barPeriod));
  const selectedInstrument = $derived(
    instrumentChoices.find((instrument) => String(instrument.id) === watchlistInstrumentId),
  );
  const selectedSavedBars = $derived(
    selectedInstrument === undefined ? undefined : findSavedBars(selectedInstrument, barPeriod),
  );
  const instrumentItems = $derived(
    instrumentChoices.map((instrument) => ({ value: String(instrument.id), label: formatWatchlistInstrument(instrument) })),
  );

  $effect(() => {
    if (!open) {
      return;
    }
    startError = '';
    void listWatchlist(fetch).then((result) => {
      if (result.kind === 'ok') {
        watchlistInstruments = result.value;
        watchlistMessage = '';
      } else {
        watchlistMessage = result.message;
      }
    });
    void readPaperCapital(fetch).then((paperCapital) => {
      paperCapitalUsd = paperCapital ?? '';
    });
  });

  // A change of the bar period can remove the selected instrument from the choices.
  $effect(() => {
    if (watchlistInstrumentId !== '' && selectedInstrument === undefined) {
      watchlistInstrumentId = '';
    }
  });

  async function runBacktest(): Promise<void> {
    if (strategyVersionId === null || selectedInstrument === undefined || startDate === '' || endDate === '') {
      startError = 'Select an instrument and a date range.';
      return;
    }
    isStarting = true;
    const result = await startBacktest(fetch, {
      strategy_version_id: strategyVersionId,
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
      startError = result.message;
      return;
    }
    onStarted(result.value);
    onOpenChange(false);
  }
</script>

<Dialog
  {open}
  {onOpenChange}
  {title}
  size="md"
  primaryText="Run backtest"
  busy={isStarting}
  onPrimary={() => {
    void runBacktest();
  }}
>
  <div class="backtest-fields">
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
    <p class="fields-note cds--form__helper-text" role="status">
      {#if watchlistMessage !== ''}
        {watchlistMessage}
      {:else if instrumentChoices.length === 0}
        No watchlist instrument has saved bars of this bar period.
      {:else if selectedSavedBars !== undefined}
        {describeSavedBars(selectedSavedBars)}
      {/if}
    </p>
    <TextInput label="Start date (UTC)" type="date" bind:value={startDate} required />
    <TextInput label="End date (UTC)" type="date" bind:value={endDate} required />
    <TextInput label="Paper capital (USD)" inputmode="decimal" class="number" bind:value={paperCapitalUsd} required />
  </div>
  {#if startError !== ''}
    <InlineNotification kind="error" lowContrast title="Backtest not started" subtitle={startError} />
  {/if}
</Dialog>

<style>
  .backtest-fields {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--cds-spacing-05);
    margin-block-end: var(--cds-spacing-05);
  }

  .backtest-fields :global(input.number) {
    font-variant-numeric: tabular-nums;
    text-align: end;
  }

  .fields-note {
    grid-column: 1 / -1;
    margin: 0;
  }
</style>
