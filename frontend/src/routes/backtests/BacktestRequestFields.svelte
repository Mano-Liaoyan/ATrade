<!-- The fields of a backtest start: the "New backtest" dialog and the "New parameter sweep" dialog have them. The
     fields combine strategy versions (strategy), bar periods (market_data), watchlist instruments with saved bars
     (watchlist), and the paper capital (paper_trading). A backtest reads only saved bars, so the fields offer only
     instruments with saved bars of the selected bar period (docs/architecture/backtest.md section 10.6). With
     `strategyVersion`, each open selects that strategy version. The source order starts at the global source order
     and changes only this start. The Instruments select picks one instrument, the top N US instruments by trading
     value, or all watchlist instruments with saved bars (docs/architecture/backtest.md section 10.10.7). The parent
     form gets the request and the block reason with onRequestChange each time they change. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import {
    checkTopN,
    convertDateToUtcStart,
    formatUniverseRange,
    readUsUniverseRange,
    type BacktestRequest,
    type UsUniverseRange,
  } from '#lib/backtest';
  import { Select, TextInput, type NotificationMessage } from '#lib/foundation/carbon';
  import {
    BAR_PERIODS,
    DEFAULT_BAR_PERIOD,
    formatSourceOrder,
    listSourceOrders,
    readSourceOrder,
    type BarPeriod,
    type BarSource,
    SurvivorshipBiasWarning,
  } from '#lib/market_data';
  import { readPaperCapital } from '#lib/paper_trading';
  import {
    formatVersionLabel,
    listStrategies,
    readStrategy,
    type StrategyDetail,
    type StrategyListItem,
    type StrategyVersionKey,
  } from '#lib/strategy';
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
    onError: (error: NotificationMessage | null) => void;
    /**
     * The request of the fields (null while a strategy version or the instrument is not selected, or N is wrong) and
     * why the start cannot run (a wrong N, which the N field shows), or null.
     */
    onRequestChange: (request: BacktestRequest | null, blockReason: string | null) => void;
    strategyVersion?: StrategyVersionKey | null;
    /** The selected strategy version ID, or an empty text. */
    strategyVersionId?: string;
  }

  let { open, onError, onRequestChange, strategyVersion = null, strategyVersionId = $bindable('') }: Props = $props();

  let strategies: StrategyListItem[] = $state([]);
  let selectedStrategy = $state<StrategyDetail | null>(null);
  let strategyId = $state('');
  let watchlistInstruments: WatchlistInstrument[] = $state([]);
  let watchlistMessage = $state('Loading the watchlist.');
  let watchlistInstrumentId = $state('');
  let barPeriod = $state<BarPeriod>(DEFAULT_BAR_PERIOD);
  let startDate = $state('');
  let endDate = $state('');
  let paperCapitalUsd = $state('');
  // The choices start with the global source order, the default of a backtest (docs/architecture/backtest.md 10.12).
  let sourceOrders: BarSource[][] = $state([]);
  let sourceOrderKey = $state('');
  // The disabled source order select says why it has no choices.
  let sourceOrderPlaceholder = $state('Reading the source order');
  type UniverseChoice = 'single' | 'rule' | 'list';
  const UNIVERSE_ITEMS: { value: UniverseChoice; label: string }[] = [
    { value: 'single', label: 'One instrument' },
    { value: 'rule', label: 'Top N by trading value' },
    { value: 'list', label: 'Watchlist' },
  ];
  let universeChoice = $state<UniverseChoice>('single');
  let topNText = $state('500');
  let universeRange = $state<UsUniverseRange | null>(null);
  const topNCheck = $derived(checkTopN(topNText));
  const topNReason = $derived(universeChoice === 'rule' && topNCheck.kind === 'refused' ? topNCheck.reason : null);

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
  const sourceOrderItems = $derived(
    sourceOrders.map((sourceOrder) => ({ value: sourceOrder.join(','), label: formatSourceOrder(sourceOrder) })),
  );
  const selectedSourceOrder = $derived(sourceOrders.find((sourceOrder) => sourceOrder.join(',') === sourceOrderKey));
  const instrumentItems = $derived(
    instrumentChoices.map((instrument) => ({ value: String(instrument.id), label: formatWatchlistInstrument(instrument) })),
  );

  $effect(() => {
    onRequestChange(readRequest(), topNReason);
  });

  // Each open reads the choices again: a strategy or a watchlist instrument can be new.
  $effect(() => {
    if (!open) {
      return;
    }
    onError(null);
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
    void readUsUniverseRange(fetch).then((result) => {
      if (result.kind === 'ok') {
        universeRange = result.value;
      }
    });
    if (paperCapitalUsd === '') {
      void readPaperCapital(fetch).then((paperCapital) => {
        paperCapitalUsd = paperCapital ?? '';
      });
    }
  });

  // Each open starts at the global source order. Only `open` runs this effect again, so a later read of another
  // choice does not undo the selection of the user.
  $effect(() => {
    if (!open) {
      return;
    }
    void readSourceOrder(fetch).then((result) => {
      if (result.kind === 'ok') {
        sourceOrders = listSourceOrders(result.value);
        sourceOrderKey = result.value.join(',');
      } else {
        sourceOrderPlaceholder = 'Could not read the source order';
      }
    });
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
      onError({ kind: 'error', title: 'Strategy not read', subtitle: result.message });
      return;
    }
    selectedStrategy = result.value;
    const latestVersion = result.value.versions.at(-1);
    strategyVersionId = versionId ?? (latestVersion === undefined ? '' : String(latestVersion.id));
  }

  type UniverseFields = Pick<BacktestRequest, 'universe_kind' | 'symbol' | 'exchange' | 'currency' | 'top_n' | 'instruments'>;

  // The universe fields of the request. Null when the universe cannot start.
  function readUniverseFields(): UniverseFields | null {
    if (universeChoice === 'rule') {
      return topNCheck.kind === 'ok' ? { universe_kind: 'rule', top_n: topNCheck.value } : null;
    }
    if (universeChoice === 'list') {
      return {
        universe_kind: 'list',
        instruments: instrumentChoices.map(({ symbol, exchange, currency }) => ({ symbol, exchange, currency })),
      };
    }
    if (selectedInstrument === undefined) {
      return null;
    }
    const { symbol, exchange, currency } = selectedInstrument;
    return { universe_kind: 'single', symbol, exchange, currency };
  }

  /** The request of the fields, or null while it cannot start. */
  function readRequest(): BacktestRequest | null {
    if (strategyVersionId === '') {
      return null;
    }
    const universe = readUniverseFields();
    if (universe === null) {
      return null;
    }
    return {
      strategy_version_id: Number(strategyVersionId),
      ...universe,
      bar_period: barPeriod,
      start_utc: convertDateToUtcStart(startDate),
      end_utc: convertDateToUtcStart(endDate),
      paper_capital_usd: paperCapitalUsd,
      // Without a source order, the backend uses the global source order.
      ...(selectedSourceOrder === undefined ? {} : { source_order: selectedSourceOrder }),
    };
  }
</script>

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
  label="Instruments"
  items={UNIVERSE_ITEMS}
  value={universeChoice}
  onValueChange={(choice: UniverseChoice) => {
    universeChoice = choice;
  }}
/>
{#if universeChoice === 'single'}
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
{:else if universeChoice === 'rule'}
  <TextInput id="top-n" label="N" inputmode="numeric" class="number" bind:value={topNText} invalidText={topNReason} />
{/if}
{#if universeChoice === 'list'}
  <div class="form-note">
    <SurvivorshipBiasWarning />
  </div>
{/if}
<p class="form-note cds--form__helper-text" role="status" aria-label="Saved bars">
  {#if universeChoice === 'rule'}
    {formatUniverseRange(universeRange)}
  {:else if watchlistMessage !== ''}
    {watchlistMessage}
  {:else if instrumentChoices.length === 0}
    No watchlist instrument has saved {barPeriodLabel} bars. Add an instrument to the
    <a class="cds--link cds--link--sm" href={resolve('/')}>watchlist</a> and open its bar chart: the chart saves the bars.
  {:else if universeChoice === 'list'}
    {instrumentChoices.length} watchlist instruments with saved {barPeriodLabel} bars
  {:else if selectedSavedBars !== undefined}
    {describeSavedBars(selectedSavedBars)}
  {/if}
</p>
<TextInput label="Start date (UTC)" type="date" bind:value={startDate} required />
<TextInput label="End date (UTC)" type="date" bind:value={endDate} required />
<TextInput label="Paper capital (USD)" inputmode="decimal" class="number" bind:value={paperCapitalUsd} required />
<Select
  label="Source order"
  items={sourceOrderItems}
  value={sourceOrderKey}
  placeholder={sourceOrderPlaceholder}
  disabled={sourceOrderItems.length === 0}
  onValueChange={(key: string) => {
    sourceOrderKey = key;
  }}
/>

<style>
  .form-note {
    grid-column: 1 / -1;
    margin: 0;
  }
</style>
