// The state of the bar chart of a backtest or forward test page (docs/architecture/indicator.md sections 23.9.8 and
// 23.9.9): the run indicators (not saved), the favorite indicators of the saved chart indicator set, and the link with
// the Trades or Fills table: the row under the pointer or the focus, the selected row of the open run, and the universe
// member that the bar chart of a multi-instrument run shows. The page
// owns one RunChart and gives it to RunAddIndicatorButton, RunBarChart, and the table.
import { ChartIndicatorSetStore } from './chart_indicator_set_store.svelte';
import type { Instrument } from './instrument_search';
import { RunChartIndicators } from './run_chart_indicators.svelte';

/** The trade index of a table row, or null for no row, a missing row, or a row without a trade mark. */
export function findRowTrade(tradeIndexByRow: readonly (number | null)[], row: number | null): number | null {
  return row === null ? null : (tradeIndexByRow[row] ?? null);
}

/** The trades whose marks get the focus ring: the trade of the pointed row and of the selected row. */
export function findRingTrades(tradeIndexByRow: readonly (number | null)[], pointedRow: number | null, selectedRow: number | null): number[] {
  return [pointedRow, selectedRow].map((row) => findRowTrade(tradeIndexByRow, row)).filter((index) => index !== null);
}

type MemberId = Pick<Instrument, 'symbol' | 'exchange'>;

export class RunChart {
  readonly indicators = new RunChartIndicators();
  /** Only the favorite indicators of the set: the run panes are not saved. */
  readonly indicatorSet = new ChartIndicatorSetStore();
  /** The table row under the pointer or the focus. */
  pointedRow: number | null = $state(null);
  #selected: { key: string; row: number } | null = $state(null);
  #member: { key: string; symbol: string; exchange: string } | null = $state(null);

  /** Reads the catalog and the saved set. Call it in an effect. */
  load(fetchFunction: typeof fetch): void {
    this.indicators.loadCatalog(fetchFunction);
    void this.indicatorSet.load(fetchFunction);
  }

  /** The selected row of the run `key` (the run id). Another run has no selected row. */
  readSelectedRow(key: string): number | null {
    return this.#selected?.key === key ? this.#selected.row : null;
  }

  selectRow(key: string, row: number): void {
    this.#selected = { key, row };
  }

  /** The selected instrument of the run `key` in `instruments`, else the first one. */
  findInstrument<T extends MemberId>(key: string, instruments: readonly T[]): T | undefined {
    const member = this.#member;
    if (member?.key !== key) {
      return instruments[0];
    }
    return instruments.find((item) => item.symbol === member.symbol && item.exchange === member.exchange) ?? instruments[0];
  }

  selectInstrument(key: string, { symbol, exchange }: MemberId): void {
    this.#member = { key, symbol, exchange };
  }
}
