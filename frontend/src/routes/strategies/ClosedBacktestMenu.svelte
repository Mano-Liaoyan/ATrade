<!-- The "Closed backtests" icon button at the end of the backtest tab strip. It shows only while the strategy has a
     closed backtest tab. The menu lists the closed backtests the newest first, like their tabs, and then "Reopen all".
     An item opens its tab again and selects it. Then the focus goes to the selected tab of the tab list, because the
     button goes away when no tab is closed. -->
<script lang="ts">
  import RecentlyViewed16 from '@carbon/icons/es/recently-viewed/16.js';
  import { tick } from 'svelte';
  import { IconMenuButton, type IconMenuItem } from '#lib/foundation/carbon';
  import BacktestTabLabel from './BacktestTabLabel.svelte';
  import type { ResultTabItem } from './strategy_workbench';

  interface Props {
    /** The closed backtest tabs of the strategy, the newest first. */
    tabs: ResultTabItem[];
    onReopen: (backtestId: number) => void;
    onReopenAll: () => void;
  }

  const { tabs, onReopen, onReopenAll }: Props = $props();

  let anchor: HTMLSpanElement | undefined = $state();

  function reopenAndFocus(reopen: () => void): void {
    const tabList = anchor?.closest('[role="tablist"]');
    reopen();
    void tick().then(() => {
      tabList?.querySelector<HTMLElement>('[role="tab"][aria-selected="true"]')?.focus();
    });
  }

  const items = $derived<IconMenuItem[]>([
    ...tabs.map((tab) => ({
      value: tab.value,
      label: tab.label,
      onSelect: () => {
        const { backtestId } = tab;
        if (backtestId !== null) {
          reopenAndFocus(() => {
            onReopen(backtestId);
          });
        }
      },
    })),
    {
      value: 'reopen-all',
      label: 'Reopen all',
      divider: true,
      onSelect: () => {
        reopenAndFocus(onReopenAll);
      },
    },
  ]);
</script>

{#snippet itemContent(item: { value: string; label: string })}
  <BacktestTabLabel tab={tabs.find((tab) => tab.value === item.value)} label={item.label} />
{/snippet}

{#if tabs.length > 0}
  <span class="closed-backtest-menu" bind:this={anchor}>
    <IconMenuButton label="Closed backtests" icon={RecentlyViewed16} {items} {itemContent} />
  </span>
{/if}

<style>
  .closed-backtest-menu {
    display: contents;
  }
</style>
