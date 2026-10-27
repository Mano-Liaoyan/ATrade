<!-- Backtests: the form that starts a backtest, and the list of backtests with their metrics side by side. The form
     combines strategy versions (strategy), bar periods (market_data), watchlist instruments with saved bars
     (watchlist), and the paper capital (paper_trading). A backtest reads only saved bars, so the form offers only
     instruments with saved bars of the selected bar period (docs/architecture/backtest.md section 10.6). The user
     selects 2 backtests of the same strategy in the list to compare them (docs/architecture section 9.5). -->
<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import {
    BacktestLimitsForm,
    checkComparisonSelection,
    convertDateToUtcStart,
    describeBacktestStatus,
    findBacktestStatusKind,
    formatPercent,
    formatUsd,
    listBacktests,
    startBacktest,
    type Backtest,
  } from '#lib/backtest';
  import {
    Button,
    Checkbox,
    DataTable,
    InlineNotification,
    Select,
    StatusIndicator,
    TextInput,
    type TableColumn,
  } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatBarPeriod } from '#lib/foundation/value_format';
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
  import {
    formatVersionLabel,
    listStrategies,
    readStrategy,
    type StrategyDetail,
    type StrategyListItem,
  } from '#lib/strategy';

  const BACKTEST_COLUMNS: TableColumn[] = [
    { header: 'Select', isSelection: true },
    { header: 'Backtest' },
    { header: 'Strategy version' },
    { header: 'Instrument' },
    { header: 'Bar period' },
    { header: 'Status' },
    { header: 'Final equity (USD)', align: 'right' },
    { header: 'Total return', align: 'right' },
    { header: 'Max drawdown', align: 'right' },
    { header: 'Trades', align: 'right' },
  ];

  let strategies: StrategyListItem[] = $state([]);
  let selectedStrategy = $state<StrategyDetail | null>(null);
  let strategyId = $state('');
  let strategyVersionId = $state('');
  let watchlistInstruments: WatchlistInstrument[] = $state([]);
  let watchlistMessage = $state('Loading the watchlist.');
  let watchlistInstrumentId = $state('');
  let barPeriod = $state<BarPeriod>(DEFAULT_BAR_PERIOD);
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
  let startDate = $state('');
  let endDate = $state('');
  let paperCapitalUsd = $state('');
  let backtests: Backtest[] = $state([]);
  let startError = $state<{ title: string; subtitle: string } | null>(null);
  let isStarting = $state(false);
  let selectedBacktestIds: number[] = $state([]);
  const comparisonSelection = $derived(checkComparisonSelection(backtests, selectedBacktestIds));

  function toggleSelection(backtestId: number, isSelected: boolean): void {
    selectedBacktestIds = isSelected
      ? [...selectedBacktestIds, backtestId]
      : selectedBacktestIds.filter((selectedId) => selectedId !== backtestId);
  }

  async function openComparison(): Promise<void> {
    if (comparisonSelection.kind !== 'ready') {
      return;
    }
    await goto(
      resolve('/backtests/[backtestId]/comparison/[otherBacktestId]', {
        backtestId: String(comparisonSelection.firstBacktestId),
        otherBacktestId: String(comparisonSelection.secondBacktestId),
      }),
    );
  }

  $effect(() => {
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
    void readPaperCapital(fetch).then((paperCapital) => {
      paperCapitalUsd = paperCapital ?? '';
    });
    void listBacktests(fetch).then((result) => {
      if (result.kind === 'ok') {
        backtests = result.value;
      }
    });
  });

  // A change of the bar period can remove the selected instrument from the choices.
  $effect(() => {
    if (watchlistInstrumentId !== '' && selectedInstrument === undefined) {
      watchlistInstrumentId = '';
    }
  });

  async function selectStrategy(selectedId: string): Promise<void> {
    strategyId = selectedId;
    selectedStrategy = null;
    strategyVersionId = '';
    const result = await readStrategy(fetch, Number(selectedId));
    if (result.kind === 'failed') {
      startError = { title: 'Strategy not read', subtitle: result.message };
      return;
    }
    selectedStrategy = result.value;
    const latestVersion = result.value.versions.at(-1);
    strategyVersionId = latestVersion === undefined ? '' : String(latestVersion.id);
  }

  async function submitBacktest(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    // The dropdowns are not native selects, so the form checks them itself.
    if (strategyVersionId === '' || selectedInstrument === undefined) {
      startError = { title: 'Backtest not started', subtitle: 'Select a strategy version and an instrument.' };
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
      startError = { title: 'Backtest not started', subtitle: result.message };
      return;
    }
    await goto(resolve('/backtests/[backtestId]', { backtestId: String(result.value.id) }));
  }
</script>

<h1>Backtests</h1>

<form id="start-backtest" class="backtest-form" aria-label="Start a backtest" onsubmit={submitBacktest}>
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
  <div>
    <Button type="submit" size="md" disabled={isStarting}>Start backtest</Button>
  </div>
</form>
{#if startError !== null}
  <InlineNotification
    kind="error"
    title={startError.title}
    subtitle={startError.subtitle}
    lowContrast
    onClose={() => (startError = null)}
  />
{/if}

<h2 class="section-heading">Limits</h2>
<BacktestLimitsForm />

<h2 class="section-heading">All backtests</h2>
{#if backtests.length === 0}
  <p>No backtest yet.</p>
{:else}
  <div class="comparison-bar">
    <Button size="sm" disabled={comparisonSelection.kind !== 'ready'} onclick={openComparison}>
      Compare selected backtests
    </Button>
    <p class="selection-message" role="status" aria-label="Comparison selection">
      {comparisonSelection.kind === 'ready' ? 'Ready to compare.' : comparisonSelection.message}
    </p>
  </div>
  <ScrollRegion label="Backtests" maxHeight="min(24rem, 50vh)">
    <DataTable columns={BACKTEST_COLUMNS} size="sm">
      {#snippet rows()}
        {#each backtests as backtest (backtest.id)}
          <tr>
            <td class="cds--table-column-checkbox">
              <Checkbox
                label={`Select backtest #${String(backtest.id)}`}
                hideLabel
                checked={selectedBacktestIds.includes(backtest.id)}
                onCheckedChange={(isSelected: boolean) => {
                  toggleSelection(backtest.id, isSelected);
                }}
              />
            </td>
            <th scope="row">
              <a class="cds--link" href={resolve('/backtests/[backtestId]', { backtestId: String(backtest.id) })}>#{backtest.id}</a>
            </th>
            <td>{formatVersionLabel(backtest.strategy_name, backtest.version_number)}</td>
            <td>{backtest.symbol} / {backtest.exchange} / {backtest.currency}</td>
            <td>{formatBarPeriod(backtest.bar_period)}</td>
            <td>
              <StatusIndicator label={describeBacktestStatus(backtest.status)} kind={findBacktestStatusKind(backtest.status)} />
            </td>
            <td align="right">{backtest.metrics === null ? '' : formatUsd(backtest.metrics.final_equity_usd)}</td>
            <td align="right">{backtest.metrics === null ? '' : formatPercent(backtest.metrics.total_return_percent)}</td>
            <td align="right">{backtest.metrics === null ? '' : formatPercent(backtest.metrics.max_drawdown_percent)}</td>
            <td align="right">{backtest.metrics === null ? '' : backtest.metrics.trade_count}</td>
          </tr>
        {/each}
      {/snippet}
    </DataTable>
  </ScrollRegion>
{/if}

<style>
  .section-heading {
    margin-block: var(--cds-spacing-07) var(--cds-spacing-05);
    font-size: var(--cds-heading-03-font-size);
    font-weight: var(--cds-heading-03-font-weight);
    line-height: var(--cds-heading-03-line-height);
    letter-spacing: var(--cds-heading-03-letter-spacing);
  }

  .backtest-form {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(12rem, 1fr));
    align-items: end;
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

  .comparison-bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--cds-spacing-05);
    margin-block-end: var(--cds-spacing-03);
  }

  .selection-message {
    margin: 0;
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    letter-spacing: var(--cds-body-compact-01-letter-spacing);
    color: var(--cds-text-secondary);
  }
</style>
