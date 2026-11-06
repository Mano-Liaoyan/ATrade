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
  #strategy = $state<StrategyDetail | null>(null);
  #version = $state<StrategyVersion | null>(null);
  #code = $state('');
  #rules = $state<StrategyRules | null>(null);
  #rulesVersionNumber = $state(0);
  #message = $state('');
  #savedRules = $state<StrategyRules | null>(null);
  #draftNotSaved = $state(false);
  #openNumber = 0;
  readonly #events: OpenStrategyEvents;

  readonly strategy = $derived(this.#strategy);
  readonly version = $derived(this.#version);
  readonly code = $derived(this.#code);
  /** The rules of the "Rules" tab, and the version that they come from (0: the blank rules, no version has rules). */
  readonly rules = $derived(this.#rules);
  readonly rulesVersionNumber = $derived(this.#rulesVersionNumber);
  /** The read error of the strategy. No panel shows it (the panels need the strategy), so the main area does. */
  readonly message = $derived(this.#message);
  /** The last write of a draft failed: the change is only in this page. */
  readonly draftNotSaved = $derived(this.#draftNotSaved);
  readonly hasUnsavedCode = $derived(this.#version !== null && this.#code !== this.#version.code);
  readonly hasUnsavedRules = $derived(this.#rules !== null && JSON.stringify(this.#rules) !== JSON.stringify(this.#savedRules));
  readonly rulesWarning = $derived(
    this.#version === null ? null : describeRulesWarning(this.#version.version_number, this.#rulesVersionNumber),
  );

  constructor(events: OpenStrategyEvents) {
    this.#events = events;
  }

  /** Closes the open strategy. The answers of each older open become stale. */
  reset(): void {
    this.#openNumber += 1;
    this.#strategy = null;
    this.#message = '';
    this.#version = null;
    this.#rules = null;
    this.#draftNotSaved = false;
  }

  /** Reads the strategy and opens a version. */
  async load(fetcher: typeof fetch, id: number, versionNumberToOpen: number | null): Promise<void> {
    this.#openNumber += 1;
    const thisOpen = this.#openNumber;
    const result = await readStrategy(fetcher, id);
    if (thisOpen !== this.#openNumber) {
      this.#writeVersions(id, result);
      return;
    }
    if (result.kind === 'failed') {
      this.#message = result.message;
      this.#events.onError(`Strategy not read: ${result.message}`);
      return;
    }
    this.#message = '';
    this.#strategy = result.value;
    const versionNumber = versionNumberToOpen ?? findDefaultVersionNumber(result.value.versions);
    if (versionNumber !== undefined) {
      await this.openVersion(fetcher, versionNumber);
    }
  }

  /** Loads the strategy again after a save. The save can end after a strategy change: then nothing happens. */
  async reload(fetcher: typeof fetch, id: number, versionNumber: number): Promise<void> {
    if (this.#strategy?.id === id) {
      await this.load(fetcher, id, versionNumber);
    }
  }

  /** Reads the strategy again. The open version stays. */
  async readVersions(fetcher: typeof fetch): Promise<void> {
    const id = this.#strategy?.id;
    if (id !== undefined) {
      this.#writeVersions(id, await readStrategy(fetcher, id));
    }
  }

  /** Reads a version of the open strategy and opens it. */
  async openVersion(fetcher: typeof fetch, versionNumber: number): Promise<void> {
    const id = this.#strategy?.id;
    if (id === undefined) {
      return;
    }
    this.#openNumber += 1;
    const thisOpen = this.#openNumber;
    const result = await readStrategyVersion(fetcher, id, versionNumber);
    if (thisOpen !== this.#openNumber) {
      return;
    }
    if (result.kind === 'failed') {
      this.#events.onError(`Version not read: ${result.message}`);
      return;
    }
    const draft = readDraft({ strategyId: id, versionNumber });
    await this.#loadRules(fetcher, id, result.value, thisOpen);
    if (thisOpen !== this.#openNumber) {
      return;
    }
    this.#version = result.value;
    this.#code = draft ?? result.value.code;
    this.#draftNotSaved = false;
    await this.#events.onVersionOpen(id, versionNumber);
  }

  readonly changeRules = (changed: StrategyRules): void => {
    this.#rules = changed;
    if (this.#strategy === null) {
      return;
    }
    const draftKey = { strategyId: this.#strategy.id, versionNumber: this.#rulesVersionNumber };
    if (JSON.stringify(changed) === JSON.stringify(this.#savedRules)) {
      clearRulesDraft(draftKey);
      this.#draftNotSaved = false;
    } else {
      this.#draftNotSaved = !writeRulesDraft(draftKey, changed);
    }
  };

  readonly changeCode = (code: string): void => {
    this.#code = code;
    if (this.#version === null) {
      return;
    }
    const draftKey = { strategyId: this.#version.strategy_id, versionNumber: this.#version.version_number };
    if (code === this.#version.code) {
      clearDraft(draftKey);
      this.#draftNotSaved = false;
    } else {
      this.#draftNotSaved = !writeDraft(draftKey, code);
    }
  };

  // A stale open of the same strategy still has the latest version list, for example of a save.
  #writeVersions(id: number, result: RequestResult<StrategyDetail>): void {
    if (result.kind === 'ok' && this.#strategy?.id === id) {
      this.#strategy = result.value;
    }
  }

  // Decided (#173): the "Rules" tab opens the rules of the open version when it has rules, or else of the latest
  // version with rules (vM), or else the blank rules. A rules draft of that version replaces them.
  async #loadRules(fetcher: typeof fetch, id: number, version: StrategyVersion, thisOpen: number): Promise<void> {
    const versionNumber = findRulesVersionNumber(this.#strategy?.versions ?? [], version.version_number);
    const result = await this.#readRules(fetcher, id, version, versionNumber);
    if (thisOpen !== this.#openNumber) {
      return;
    }
    if (result.kind === 'failed') {
      this.#events.onError(`Rules not read: ${result.message}`);
      return;
    }
    this.#rulesVersionNumber = versionNumber ?? 0;
    this.#savedRules = result.value;
    this.#rules = readRulesDraft({ strategyId: id, versionNumber: this.#rulesVersionNumber }) ?? result.value;
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
