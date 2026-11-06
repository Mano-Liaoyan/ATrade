// The diff tab of the editor panel for a diff card of the AI assistant (docs/architecture/assistant.md 25.5.2): the
// new version and the version before it. The tab stays until Keep or Discard of that card, or a strategy change.
import { readStrategyVersion } from '#lib/strategy';

export const DIFF_TAB_VALUE = 'diff';

export interface VersionDiff {
  versionNumber: number;
  firstCode: string;
  secondCode: string;
}

export class AssistantDiff {
  diff = $state<VersionDiff | null>(null);
  /** The diff tab is the selected tab of the editor panel. */
  isSelected = $state(false);
  #requestNumber = 0;

  readonly tab = $derived(
    this.diff === null
      ? null
      : { value: DIFF_TAB_VALUE, label: `v${String(this.diff.versionNumber - 1)} → v${String(this.diff.versionNumber)}` },
  );

  /** Reads both versions and selects the diff tab. Returns the error text, or null. A newer open or a close drops the
   answer. */
  async open(fetcher: typeof fetch, strategyId: number, versionNumber: number): Promise<string | null> {
    this.#requestNumber += 1;
    const thisRequest = this.#requestNumber;
    const [before, after] = await Promise.all([
      readStrategyVersion(fetcher, strategyId, versionNumber - 1),
      readStrategyVersion(fetcher, strategyId, versionNumber),
    ]);
    if (thisRequest !== this.#requestNumber) {
      return null;
    }
    if (before.kind === 'failed') {
      return before.message;
    }
    if (after.kind === 'failed') {
      return after.message;
    }
    this.diff = { versionNumber, firstCode: before.value.code, secondCode: after.value.code };
    this.isSelected = true;
    return null;
  }

  /** Closes the diff tab. With a version number, only when the tab shows that version. */
  close(versionNumber?: number): void {
    this.#requestNumber += 1;
    if (versionNumber === undefined || this.diff?.versionNumber === versionNumber) {
      this.diff = null;
      this.isSelected = false;
    }
  }
}
