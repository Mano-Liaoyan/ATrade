// The open strategy: delayed reads of a strategy or version that is not open any more change nothing.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vite-plus/test';
import { readDraft, type StrategyRules } from '#lib/strategy';
import { OpenStrategy } from './open_strategy.svelte';

const RULES = { entry: 'rules of the fake backend' } as unknown as StrategyRules;

interface FakeBackend {
  fetchFunction: typeof fetch;
  /** Answers the waiting read of the path. */
  answer: (path: string, status?: number, body?: unknown) => Promise<void>;
}

function findAnswerBody(path: string): unknown {
  const match = /\/strategies\/(\d+)(?:\/versions\/(\d+))?$/.exec(path);
  const strategyId = Number(match?.[1]);
  if (match?.[2] === undefined) {
    return {
      id: strategyId,
      name: `Strategy ${String(strategyId)}`,
      versions: [
        { version_number: 1, source: 'rule_builder', discarded: false },
        { version_number: 2, source: 'code', discarded: false },
      ],
    };
  }
  const versionNumber = Number(match[2]);
  return {
    id: strategyId * 100 + versionNumber,
    strategy_id: strategyId,
    version_number: versionNumber,
    code: `code ${String(strategyId)}.${String(versionNumber)}`,
    rules: versionNumber === 1 ? RULES : null,
  };
}

function createBackend(): FakeBackend {
  const waiting = new Map<string, (response: Response) => void>();
  const fetchFunction: typeof fetch = (input) =>
    new Promise((resolve) => {
      waiting.set(input as string, resolve);
    });
  return {
    fetchFunction,
    answer: async (path, status = 200, body) => {
      const fullPath = `/api/strategies/${path}`;
      const answer = waiting.get(fullPath);
      if (answer === undefined) {
        throw new Error(`No waiting read of ${fullPath}. Waiting: ${[...waiting.keys()].join(', ')}`);
      }
      waiting.delete(fullPath);
      const shownBody = status === 200 ? (body ?? findAnswerBody(fullPath)) : { detail: 'Read failed.' };
      answer(new Response(JSON.stringify(shownBody), { status }));
      await settle();
    },
  };
}

async function settle(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve));
}

function createOpenStrategy(): { openStrategy: OpenStrategy; errors: string[]; openedVersions: string[] } {
  const errors: string[] = [];
  const openedVersions: string[] = [];
  const openStrategy = new OpenStrategy({
    onError: (text) => {
      errors.push(text);
    },
    onVersionOpen: (id, versionNumber) => {
      openedVersions.push(`${String(id)}.${String(versionNumber)}`);
      return Promise.resolve();
    },
  });
  return { openStrategy, errors, openedVersions };
}

async function createLoadedOpenStrategy(backend: FakeBackend): Promise<ReturnType<typeof createOpenStrategy>> {
  const created = createOpenStrategy();
  const load = created.openStrategy.load(backend.fetchFunction, 1, 1);
  await backend.answer('1');
  await backend.answer('1/versions/1');
  await load;
  return created;
}

const NEW_VERSION_LIST = {
  id: 1,
  name: 'Strategy 1',
  versions: [
    { version_number: 1, source: 'rule_builder', discarded: false },
    { version_number: 2, source: 'code', discarded: false },
    { version_number: 3, source: 'code', discarded: false },
  ],
};

describe('OpenStrategy', () => {
  beforeEach(() => {
    const values = new Map<string, string>();
    vi.stubGlobal('localStorage', {
      getItem: (key: string) => values.get(key) ?? null,
      removeItem: (key: string) => values.delete(key),
      setItem: (key: string, value: string) => values.set(key, value),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('keeps the strategy, version, and code of the new strategy when the reads of two strategies interleave', async () => {
    const backend = createBackend();
    const { openStrategy, openedVersions } = createOpenStrategy();
    const firstLoad = openStrategy.load(backend.fetchFunction, 1, null);
    openStrategy.reset();
    const secondLoad = openStrategy.load(backend.fetchFunction, 2, null);

    await backend.answer('2');
    await backend.answer('2/versions/2');
    await backend.answer('1');
    await backend.answer('2/versions/1');

    expect(openStrategy.strategy?.id).toBe(2);
    expect(openStrategy.version?.strategy_id).toBe(2);
    expect(openStrategy.code).toBe('code 2.2');
    expect(openedVersions).toEqual(['2.2']);
    await firstLoad;
    await secondLoad;
  });

  it('drops the read error of the old strategy', async () => {
    const backend = createBackend();
    const { openStrategy, errors } = createOpenStrategy();
    void openStrategy.load(backend.fetchFunction, 1, null);
    openStrategy.reset();
    await backend.answer('1', 404);

    expect(openStrategy.message).toBe('');
    expect(errors).toEqual([]);
  });

  it('drops a version read of the old strategy that ends after the new strategy opened', async () => {
    const backend = createBackend();
    const { openStrategy, openedVersions } = createOpenStrategy();
    const firstLoad = openStrategy.load(backend.fetchFunction, 1, null);
    await backend.answer('1');
    openStrategy.reset();
    const secondLoad = openStrategy.load(backend.fetchFunction, 2, null);
    await backend.answer('2');
    await backend.answer('2/versions/2');
    await backend.answer('2/versions/1');
    await backend.answer('1/versions/2');

    expect(openStrategy.strategy?.id).toBe(2);
    expect(openStrategy.code).toBe('code 2.2');
    expect(openedVersions).toEqual(['2.2']);
    await firstLoad;
    await secondLoad;
  });

  it('drops a rules read and its error after a strategy change', async () => {
    const backend = createBackend();
    const { openStrategy, errors, openedVersions } = createOpenStrategy();
    const load = openStrategy.load(backend.fetchFunction, 1, null);
    await backend.answer('1');
    await backend.answer('1/versions/2');
    openStrategy.reset();
    await backend.answer('1/versions/1', 500);

    expect(openStrategy.version).toBeNull();
    expect(errors).toEqual([]);
    expect(openedVersions).toEqual([]);
    await load;
  });

  it('opens the last selected version of a strategy', async () => {
    const backend = createBackend();
    const { openStrategy, openedVersions } = await createLoadedOpenStrategy(backend);
    const firstOpen = openStrategy.openVersion(backend.fetchFunction, 2);
    const secondOpen = openStrategy.openVersion(backend.fetchFunction, 1);
    await backend.answer('1/versions/1');
    await backend.answer('1/versions/2');

    expect(openStrategy.code).toBe('code 1.1');
    expect(openedVersions).toEqual(['1.1', '1.1']);
    await firstOpen;
    await secondOpen;
  });

  it('keeps the version list of a save when a version pick replaces the save read', async () => {
    const backend = createBackend();
    const { openStrategy } = await createLoadedOpenStrategy(backend);
    const reload = openStrategy.reload(backend.fetchFunction, 1, 3);
    const pick = openStrategy.openVersion(backend.fetchFunction, 2);
    await backend.answer('1', 200, NEW_VERSION_LIST);
    await backend.answer('1/versions/2');
    await backend.answer('1/versions/1');
    await Promise.all([reload, pick]);

    expect(openStrategy.strategy?.versions).toHaveLength(3);
    expect(openStrategy.code).toBe('code 1.2');
  });

  it('keeps the version list of a Discard when a version pick starts during the read', async () => {
    const backend = createBackend();
    const { openStrategy } = await createLoadedOpenStrategy(backend);
    const read = openStrategy.readVersions(backend.fetchFunction);
    const pick = openStrategy.openVersion(backend.fetchFunction, 1);
    await backend.answer('1', 200, NEW_VERSION_LIST);
    await backend.answer('1/versions/1');
    await Promise.all([read, pick]);

    expect(openStrategy.strategy?.versions).toHaveLength(3);
  });

  it('does not open the saved strategy when the save ends after a strategy change', async () => {
    const backend = createBackend();
    const { openStrategy } = await createLoadedOpenStrategy(backend);
    openStrategy.reset();
    const secondLoad = openStrategy.load(backend.fetchFunction, 2, 1);
    await backend.answer('2');

    void openStrategy.reload(backend.fetchFunction, 1, 1);
    await backend.answer('2/versions/1');

    expect(openStrategy.strategy?.id).toBe(2);
    expect(openStrategy.code).toBe('code 2.1');
    await secondLoad;
  });

  it('drops a read of the version list after a strategy change', async () => {
    const backend = createBackend();
    const { openStrategy } = await createLoadedOpenStrategy(backend);
    const read = openStrategy.readVersions(backend.fetchFunction);
    openStrategy.reset();
    await backend.answer('1');
    await read;

    expect(openStrategy.strategy).toBeNull();
  });

  it('opens the version when the rules read fails, and reports the error', async () => {
    const backend = createBackend();
    const { openStrategy, errors, openedVersions } = createOpenStrategy();
    const load = openStrategy.load(backend.fetchFunction, 1, null);
    await backend.answer('1');
    await backend.answer('1/versions/2');
    await backend.answer('1/versions/1', 500);

    await load;
    expect(openStrategy.code).toBe('code 1.2');
    expect(errors).toEqual(['Rules not read: Read failed.']);
    expect(openedVersions).toEqual(['1.2']);
  });

  it('keeps the text that the user typed during a save as a draft of the new version', async () => {
    const backend = createBackend();
    const { openStrategy } = await createLoadedOpenStrategy(backend);
    openStrategy.changeCode('sent code');
    // The save takes time. The POST has the sent code, and the user types more.
    openStrategy.changeCode('sent code and more');

    const reload = openStrategy.reload(backend.fetchFunction, 1, 2, 'sent code');
    await backend.answer('1');
    await backend.answer('1/versions/2', 200, { id: 102, strategy_id: 1, version_number: 2, code: 'sent code', rules: null });
    await backend.answer('1/versions/1');
    await reload;

    expect(openStrategy.version?.version_number).toBe(2);
    expect(openStrategy.code).toBe('sent code and more');
    expect(readDraft({ strategyId: 1, versionNumber: 2 })).toBe('sent code and more');
  });

  it('opens the saved code when the user typed nothing during the save', async () => {
    const backend = createBackend();
    const { openStrategy } = await createLoadedOpenStrategy(backend);
    openStrategy.changeCode('sent code');

    const reload = openStrategy.reload(backend.fetchFunction, 1, 2, 'sent code');
    await backend.answer('1');
    await backend.answer('1/versions/2', 200, { id: 102, strategy_id: 1, version_number: 2, code: 'sent code', rules: null });
    await backend.answer('1/versions/1');
    await reload;

    expect(openStrategy.code).toBe('sent code');
    expect(openStrategy.hasUnsavedCode).toBe(false);
    expect(readDraft({ strategyId: 1, versionNumber: 2 })).toBeNull();
  });

  it('keeps a code draft for the open version and opens it again', async () => {
    const backend = createBackend();
    const { openStrategy } = await createLoadedOpenStrategy(backend);
    openStrategy.changeCode('edited code');
    const open = openStrategy.openVersion(backend.fetchFunction, 1);
    await backend.answer('1/versions/1');
    await open;

    expect(openStrategy.code).toBe('edited code');
    expect(openStrategy.hasUnsavedCode).toBe(true);
  });
});
