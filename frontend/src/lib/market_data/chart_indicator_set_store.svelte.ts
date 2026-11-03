// The saved chart indicator set of a page (docs/architecture/indicator.md section 23.9.7). The instrument page uses
// the panes and the favorites. A backtest or forward test chart uses only the favorites: its own panes are not saved,
// and a favorite change sends the saved panes back unchanged.
import { EMPTY_CHART_INDICATOR_SET, readChartIndicatorSet, saveChartIndicatorSet, toggleFavorite } from './chart_indicator_set';
import type { ChartPane } from './chart_indicators';

export class ChartIndicatorSetStore {
  panes: ChartPane[] = $state(EMPTY_CHART_INDICATOR_SET.panes);
  favorites: string[] = $state(EMPTY_CHART_INDICATOR_SET.favorites);
  /** The message of the last failed read or save. A later good save removes it. */
  errorText: string | null = $state(null);
  #isLoaded = false;
  #arePanesChanged = false;
  #areFavoritesChanged = false;
  #loading: Promise<boolean> | null = null;
  // Each PUT starts after the read and after the PUT before it, and sends the set at that time. So the last change is
  // the last saved set, and a change before the read answer keeps the saved part that did not change.
  #saving: Promise<void> = Promise.resolve();

  /** Reads the saved set. A part (panes or favorites) that changed before the answer keeps the change. */
  load(fetchFunction: typeof fetch): Promise<boolean> {
    if (this.#isLoaded) {
      return Promise.resolve(true);
    }
    this.#loading ??= readChartIndicatorSet(fetchFunction).then((result) => {
      this.#loading = null;
      if (result.kind === 'failed') {
        this.errorText = result.message;
        return false;
      }
      this.#isLoaded = true;
      if (!this.#arePanesChanged) {
        this.panes = result.value.panes;
      }
      if (!this.#areFavoritesChanged) {
        this.favorites = result.value.favorites;
      }
      return true;
    });
    return this.#loading;
  }

  /** Shows the panes at once and saves them. A failed save keeps the change and sets `errorText`. */
  changePanes(fetchFunction: typeof fetch, panes: ChartPane[]): void {
    this.panes = panes;
    this.#arePanesChanged = true;
    this.#save(fetchFunction);
  }

  /** Adds or removes a favorite at once and saves it with the saved panes. When the read of the saved set fails, the
   * favorites are not saved. */
  toggleFavorite(fetchFunction: typeof fetch, key: string): void {
    this.favorites = toggleFavorite(this.favorites, key);
    this.#areFavoritesChanged = true;
    this.#save(fetchFunction);
  }

  #save(fetchFunction: typeof fetch): void {
    this.#saving = this.#saving.then(async () => {
      // Without the saved set, only a pane change is saved: a favorite change would save over the saved panes.
      if (!(await this.load(fetchFunction)) && !this.#arePanesChanged) {
        return;
      }
      const result = await saveChartIndicatorSet(fetchFunction, $state.snapshot({ panes: this.panes, favorites: this.favorites }));
      this.errorText = result.kind === 'ok' ? null : result.message;
    });
  }
}
