// The closed backtest tabs of each strategy on the strategy page. A closed tab is only hidden; the backtest stays. The
// browser keeps the list (CLOSED_BACKTEST_TABS_STORAGE_KEY), so it stays after a reload.
import { readStoredLayout, writeStoredLayout } from '#lib/foundation/workbench';
import {
  CLOSED_BACKTEST_TABS_STORAGE_KEY,
  closeBacktestTab,
  findClosedBacktestIds,
  openBacktestTab,
  readClosedBacktestTabs,
  reopenAllBacktestTabs,
  type ClosedBacktestTabs,
  type ResultSelection,
} from './strategy_workbench';

export class ClosedBacktestTabsState {
  #closed = $state(readClosedBacktestTabs(readStoredLayout(CLOSED_BACKTEST_TABS_STORAGE_KEY)));

  ids(strategyId: number | null): ReadonlySet<number> {
    return findClosedBacktestIds(this.#closed, strategyId);
  }

  close(strategyId: number, backtestId: number): void {
    this.#write(closeBacktestTab(this.#closed, strategyId, backtestId));
  }

  /** A backtest that opens from elsewhere: its tab opens again. Returns the selection of its tab. */
  open(strategyId: number, backtestId: number): ResultSelection {
    const opened = openBacktestTab(this.#closed, strategyId, backtestId);
    this.#write(opened.closed);
    return opened.selection;
  }

  reopenAll(strategyId: number | null): void {
    if (strategyId !== null) {
      this.#write(reopenAllBacktestTabs(this.#closed, strategyId));
    }
  }

  #write(closed: ClosedBacktestTabs): void {
    if (closed !== this.#closed) {
      this.#closed = closed;
      writeStoredLayout(CLOSED_BACKTEST_TABS_STORAGE_KEY, closed);
    }
  }
}
