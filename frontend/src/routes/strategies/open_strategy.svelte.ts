// The open strategy of the strategy workbench: the strategy, its open version, the editor code, the rules, and their
// drafts. A change of strategy keeps the workbench mounted, so the reads of two strategies can overlap. Each open takes
// a number, and the answers of an older open are stale: they change nothing and report nothing.
import {
  BLANK_RULES,
  clearDraft,
  clearRulesDraft,
  describeRulesWarning,
  findRulesVersionNumber,
  readDraft,
  readRulesDraft,
  readStrategy,
  readStrategyVersion,
  writeDraft,
  writeRulesDraft,
  type RequestResult,
  type StrategyDetail,
  type StrategyRules,
  type StrategyVersion,
} from '#lib/strategy';
import { findDefaultVersionNumber } from './strategy_workbench';

export interface OpenStrategyEvents {
  onError: (text: string) => void;
  /** A version opened. The open ends when this ends. */
  onVersionOpen: (strategyId: number, versionNumber: number) => Promise<void>;
}

export class OpenStrategy {
  strategy = $state<StrategyDetail | null>(null);
  version = $state<StrategyVersion | null>(null);
  code = $state('');
  /** The rules of the "Rules" tab, and the version that they come from (0: the blank rules, no version has rules). */
  rules = $state<StrategyRules | null>(null);
  rulesVersionNumber = $state(0);
  /** The read error of the strategy. No panel shows it (the panels need the strategy), so the main area does. */
  message = $state('');
  #savedRules = $state<StrategyRules | null>(null);
  #openNumber = 0;
  readonly #events: OpenStrategyEvents;

  readonly hasUnsavedCode = $derived(this.version !== null && this.code !== this.version.code);
  readonly hasUnsavedRules = $derived(this.rules !== null && JSON.stringify(this.rules) !== JSON.stringify(this.#savedRules));
  readonly rulesWarning = $derived(
    this.version === null ? null : describeRulesWarning(this.version.version_number, this.rulesVersionNumber),
  );

  constructor(events: OpenStrategyEvents) {
    this.#events = events;
  }

  /** Closes the open strategy. The answers of each older open become stale. */
  reset(): void {
    this.#openNumber += 1;
    this.strategy = null;
    this.message = '';
    this.version = null;
    this.rules = null;
  }

  /** Reads the strategy and opens a version. Returns false when the open is stale. */
  async load(fetcher: typeof fetch, id: number, versionNumberToOpen: number | null): Promise<boolean> {
    this.#openNumber += 1;
    const thisOpen = this.#openNumber;
    const result = await readStrategy(fetcher, id);
    if (thisOpen !== this.#openNumber) {
      return false;
    }
    if (result.kind === 'failed') {
      this.message = result.message;
      this.#events.onError(`Strategy not read: ${result.message}`);
      return true;
    }
    this.message = '';
    this.strategy = result.value;
    const versionNumber = versionNumberToOpen ?? findDefaultVersionNumber(result.value.versions);
    return versionNumber === undefined ? true : this.openVersion(fetcher, id, versionNumber);
  }

  /** Loads the strategy again after a save. The save can end after a strategy change: then nothing happens. */
  async reload(fetcher: typeof fetch, id: number, versionNumber: number): Promise<void> {
    if (this.strategy?.id === id) {
      await this.load(fetcher, id, versionNumber);
    }
  }

  /** Reads the strategy again. The open version stays. */
  async readVersions(fetcher: typeof fetch, id: number): Promise<void> {
    const thisOpen = this.#openNumber;
    const result = await readStrategy(fetcher, id);
    if (thisOpen === this.#openNumber && result.kind === 'ok') {
      this.strategy = result.value;
    }
  }

  /** Reads a version and opens it. Returns false when the open is stale. */
  async openVersion(fetcher: typeof fetch, id: number, versionNumber: number): Promise<boolean> {
    this.#openNumber += 1;
    const thisOpen = this.#openNumber;
    const result = await readStrategyVersion(fetcher, id, versionNumber);
    if (thisOpen !== this.#openNumber) {
      return false;
    }
    if (result.kind === 'failed') {
      this.#events.onError(`Version not read: ${result.message}`);
      return true;
    }
    const draft = readDraft(localStorage, { strategyId: id, versionNumber });
    await this.#loadRules(fetcher, id, result.value, thisOpen);
    if (thisOpen !== this.#openNumber) {
      return false;
    }
    this.version = result.value;
    this.code = draft ?? result.value.code;
    await this.#events.onVersionOpen(id, versionNumber);
    return thisOpen === this.#openNumber;
  }

  readonly changeRules = (changed: StrategyRules): void => {
    this.rules = changed;
    if (this.strategy === null) {
      return;
    }
    const draftKey = { strategyId: this.strategy.id, versionNumber: this.rulesVersionNumber };
    if (JSON.stringify(changed) === JSON.stringify(this.#savedRules)) {
      clearRulesDraft(localStorage, draftKey);
    } else {
      writeRulesDraft(localStorage, draftKey, changed);
    }
  };

  readonly changeCode = (code: string): void => {
    this.code = code;
    if (this.version === null) {
      return;
    }
    const draftKey = { strategyId: this.version.strategy_id, versionNumber: this.version.version_number };
    if (code === this.version.code) {
      clearDraft(localStorage, draftKey);
    } else {
      writeDraft(localStorage, draftKey, code);
    }
  };

  // Decided (#173): the "Rules" tab opens the rules of the open version when it has rules, or else of the latest
  // version with rules (vM), or else the blank rules. A rules draft of that version replaces them.
  async #loadRules(fetcher: typeof fetch, id: number, version: StrategyVersion, thisOpen: number): Promise<void> {
    const versionNumber = findRulesVersionNumber(this.strategy?.versions ?? [], version.version_number);
    const result = await this.#readRules(fetcher, id, version, versionNumber);
    if (thisOpen !== this.#openNumber) {
      return;
    }
    if (result.kind === 'failed') {
      this.#events.onError(`Rules not read: ${result.message}`);
      return;
    }
    this.rulesVersionNumber = versionNumber ?? 0;
    this.#savedRules = result.value;
    this.rules = readRulesDraft(localStorage, { strategyId: id, versionNumber: this.rulesVersionNumber }) ?? result.value;
  }

  async #readRules(
    fetcher: typeof fetch,
    id: number,
    version: StrategyVersion,
    versionNumber: number | null,
  ): Promise<RequestResult<StrategyRules>> {
    if (versionNumber === null) {
      return { kind: 'ok', value: BLANK_RULES };
    }
    if (versionNumber === version.version_number && version.rules !== null) {
      return { kind: 'ok', value: version.rules as StrategyRules };
    }
    const result = await readStrategyVersion(fetcher, id, versionNumber);
    return result.kind === 'failed' ? result : { kind: 'ok', value: (result.value.rules ?? BLANK_RULES) as StrategyRules };
  }
}
