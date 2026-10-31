<!-- The text of a backtest tab, and of its item in the "Closed backtests" menu: the status icon in front of the name,
     with no status word (its name and tooltip give the status), the name, and the total return as ChangeText.
     Trades, Orders, and Logs have no status: they show only their label. -->
<script lang="ts">
  import { describeBacktestStatus, findBacktestStatusKind } from '#lib/backtest';
  import { StatusIndicator } from '#lib/foundation/carbon';
  import { ChangeText } from '#lib/foundation/value_format';
  import type { ResultTabItem } from './strategy_workbench';

  const { tab, label }: { tab: ResultTabItem | undefined; label: string } = $props();
</script>

{#if tab === undefined || tab.status === null}
  {label}
{:else}
  <span class="result-tab-label">
    <StatusIndicator kind={findBacktestStatusKind(tab.status)} label={describeBacktestStatus(tab.status)} iconOnly />
    {tab.name}
    {#if tab.changeText !== ''}
      <ChangeText value={tab.change} text={tab.changeText} />
    {/if}
  </span>
{/if}

<style>
  .result-tab-label {
    display: inline-flex;
    align-items: center;
    gap: var(--cds-spacing-03);
  }
</style>
