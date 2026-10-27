<!-- Backtests: the form that starts a backtest, and the list of backtests with their metrics side by side. The form
     combines strategy versions (strategy), bar periods (market_data), and the paper capital (paper_trading). The user
     selects 2 backtests of the same strategy in the list to compare them (docs/architecture section 9.5). -->
<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import {
    BacktestLimitsForm,
    checkComparisonSelection,
    convertDateToUtcStart,
    describeBacktestStatus,
    formatPercent,
    formatUsd,
    listBacktests,
    startBacktest,
    type Backtest,
  } from '#lib/backtest';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { BAR_PERIODS, DEFAULT_BAR_PERIOD, type BarPeriod } from '#lib/market_data';
  import { readPaperCapital } from '#lib/paper_trading';
  import {
    formatVersionLabel,
    listStrategies,
    readStrategy,
    type StrategyDetail,
    type StrategyListItem,
  } from '#lib/strategy';

  let strategies: StrategyListItem[] = $state([]);
  let selectedStrategy = $state<StrategyDetail | null>(null);
  let strategyId = $state('');
  let strategyVersionId = $state('');
  let symbol = $state('');
  let exchange = $state('');
  let currency = $state('USD');
  let barPeriod = $state<BarPeriod>(DEFAULT_BAR_PERIOD);
  let startDate = $state('');
  let endDate = $state('');
  let paperCapitalUsd = $state('');
  let backtests: Backtest[] = $state([]);
  let errorMessage = $state('');
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
    void readPaperCapital(fetch).then((paperCapital) => {
      paperCapitalUsd = paperCapital ?? '';
    });
    void listBacktests(fetch).then((result) => {
      if (result.kind === 'ok') {
        backtests = result.value;
      }
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

  async function submitBacktest(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    isStarting = true;
    errorMessage = '';
    const result = await startBacktest(fetch, {
      strategy_version_id: Number(strategyVersionId),
      symbol: symbol.trim().toUpperCase(),
      exchange: exchange.trim().toUpperCase(),
      currency: currency.trim().toUpperCase(),
      bar_period: barPeriod,
      start_utc: convertDateToUtcStart(startDate),
      end_utc: convertDateToUtcStart(endDate),
      paper_capital_usd: paperCapitalUsd,
    });
    isStarting = false;
    if (result.kind === 'failed') {
      errorMessage = result.message;
      return;
    }
    await goto(resolve('/backtests/[backtestId]', { backtestId: String(result.value.id) }));
  }
</script>

<h1>Backtests</h1>

<form class="backtest-form" aria-label="Start a backtest" onsubmit={submitBacktest}>
  <!-- The select is outside its label: the name of a select inside a label would also hold the selected option. -->
  <div class="field">
    <label for="backtest-strategy">Strategy</label>
    <select id="backtest-strategy" bind:value={strategyId} onchange={selectStrategy} required>
      <option value="">Select a strategy</option>
      {#each strategies as strategy (strategy.id)}
        <option value={String(strategy.id)}>{strategy.name}</option>
      {/each}
    </select>
  </div>
  <div class="field">
    <label for="backtest-strategy-version">Strategy version</label>
    <select id="backtest-strategy-version" bind:value={strategyVersionId} required>
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
  <label>
    Bar period
    <select bind:value={barPeriod}>
      {#each BAR_PERIODS as period (period.value)}
        <option value={period.value}>{period.label}</option>
      {/each}
    </select>
  </label>
  <label>
    Start date (UTC)
    <input type="date" bind:value={startDate} required />
  </label>
  <label>
    End date (UTC)
    <input type="date" bind:value={endDate} required />
  </label>
  <label>
    Paper capital (USD)
    <input inputmode="decimal" bind:value={paperCapitalUsd} required />
  </label>
  <button type="submit" disabled={isStarting}>Start backtest</button>
</form>
{#if errorMessage !== ''}
  <p class="error" role="alert">{errorMessage}</p>
{/if}

<h2>Limits</h2>
<BacktestLimitsForm />

<h2>All backtests</h2>
{#if backtests.length === 0}
  <p>No backtest yet.</p>
{:else}
  <div class="comparison-bar">
    <button type="button" disabled={comparisonSelection.kind !== 'ready'} onclick={openComparison}>
      Compare selected backtests
    </button>
    <p class="selection-message" role="status" aria-label="Comparison selection">
      {comparisonSelection.kind === 'ready' ? 'Ready to compare.' : comparisonSelection.message}
    </p>
  </div>
  <ScrollRegion label="Backtests" maxHeight="min(24rem, 50vh)">
    <table class="backtest-list">
      <thead>
        <tr>
          <th scope="col">Select</th>
          <th scope="col">Backtest</th>
          <th scope="col">Strategy version</th>
          <th scope="col">Instrument</th>
          <th scope="col">Bar period</th>
          <th scope="col">Status</th>
          <th scope="col">Final equity (USD)</th>
          <th scope="col">Total return</th>
          <th scope="col">Max drawdown</th>
          <th scope="col">Trades</th>
        </tr>
      </thead>
      <tbody>
        {#each backtests as backtest (backtest.id)}
          <tr>
            <td>
              <input
                type="checkbox"
                aria-label={`Select backtest #${String(backtest.id)}`}
                checked={selectedBacktestIds.includes(backtest.id)}
                onchange={(event) => {
                  toggleSelection(backtest.id, event.currentTarget.checked);
                }}
              />
            </td>
            <th scope="row">
              <a href={resolve('/backtests/[backtestId]', { backtestId: String(backtest.id) })}>#{backtest.id}</a>
            </th>
            <td>{formatVersionLabel(backtest.strategy_name, backtest.version_number)}</td>
            <td>{backtest.symbol} / {backtest.exchange} / {backtest.currency}</td>
            <td>{backtest.bar_period}</td>
            <td>{describeBacktestStatus(backtest.status)}</td>
            <td class="number">{backtest.metrics === null ? '' : formatUsd(backtest.metrics.final_equity_usd)}</td>
            <td class="number">{backtest.metrics === null ? '' : formatPercent(backtest.metrics.total_return_percent)}</td>
            <td class="number">{backtest.metrics === null ? '' : formatPercent(backtest.metrics.max_drawdown_percent)}</td>
            <td class="number">{backtest.metrics === null ? '' : backtest.metrics.trade_count}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </ScrollRegion>
{/if}

<style>
  .backtest-form {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(12rem, 1fr));
    align-items: end;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }

  .backtest-form label,
  .backtest-form .field {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .error {
    color: var(--color-warning);
  }

  .comparison-bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
  }

  .selection-message {
    margin: 0;
    color: var(--color-muted);
  }

  .backtest-list {
    border-collapse: collapse;
    inline-size: 100%;
    font-size: 0.875rem;
  }

  .backtest-list th,
  .backtest-list td {
    padding: 0.375rem 0.75rem;
    border-bottom: 1px solid var(--color-border);
    text-align: start;
  }

  .backtest-list thead th {
    position: sticky;
    inset-block-start: 0;
    background: var(--color-surface);
  }

  .backtest-list .number {
    text-align: end;
    font-variant-numeric: tabular-nums;
  }
</style>
