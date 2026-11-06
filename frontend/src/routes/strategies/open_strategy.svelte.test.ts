// The open strategy: delayed reads of a strategy or version that is not open any more change nothing.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vite-plus/test';
import type { StrategyRules } from '#lib/strategy';
import { OpenStrategy } from './open_strategy.svelte';

const RULES = { entry: 'rules of the fake backend' } as unknown as StrategyRules;

interface FakeBackend {
  fetchFunction: typeof fetch;
  /** Answers the waiting read of the path. */
  answer: (path: string, status?: number) => Promise<void>;
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
    answer: async (path, status = 200) => {
      const fullPath = `/api/strategies/${path}`;
      const answer = waiting.get(fullPath);
      if (answer === undefined) {
        throw new Error(`No waiting read of ${fullPath}. Waiting: ${[...waiting.keys()].join(', ')}`);
      }
      waiting.delete(fullPath);
      answer(new Response(JSON.stringify(status === 200 ? findAnswerBody(fullPath) : { detail: 'Read failed.' }), { status }));
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
    expect(await firstLoad).toBe(false);
    expect(await secondLoad).toBe(true);
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
    expect(await firstLoad).toBe(false);
    expect(await secondLoad).toBe(true);
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
    expect(await load).toBe(false);
  });

  it('opens the last selected version of a strategy', async () => {
    const backend = createBackend();
    const { openStrategy, openedVersions } = createOpenStrategy();
    const firstOpen = openStrategy.openVersion(backend.fetchFunction, 1, 2);
    const secondOpen = openStrategy.openVersion(backend.fetchFunction, 1, 1);
    await backend.answer('1/versions/1');
    await backend.answer('1/versions/2');

    expect(openStrategy.code).toBe('code 1.1');
    expect(openedVersions).toEqual(['1.1']);
    expect(await firstOpen).toBe(false);
    expect(await secondOpen).toBe(true);
  });

  it('does not open the saved strategy when the save ends after a strategy change', async () => {
    const backend = createBackend();
    const { openStrategy } = createOpenStrategy();
    const load = openStrategy.load(backend.fetchFunction, 1, 1);
    await backend.answer('1');
    await backend.answer('1/versions/1');
    await load;
    openStrategy.reset();
    const secondLoad = openStrategy.load(backend.fetchFunction, 2, 1);
    await backend.answer('2');

    void openStrategy.reload(backend.fetchFunction, 1, 1);
    await backend.answer('2/versions/1');

    expect(openStrategy.strategy?.id).toBe(2);
    expect(openStrategy.code).toBe('code 2.1');
    expect(await secondLoad).toBe(true);
  });

  it('drops a read of the version list after a strategy change', async () => {
    const backend = createBackend();
    const { openStrategy } = createOpenStrategy();
    const load = openStrategy.load(backend.fetchFunction, 1, 1);
    await backend.answer('1');
    await backend.answer('1/versions/1');
    await load;
    const read = openStrategy.readVersions(backend.fetchFunction, 1);
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

    expect(await load).toBe(true);
    expect(openStrategy.code).toBe('code 1.2');
    expect(errors).toEqual(['Rules not read: Read failed.']);
    expect(openedVersions).toEqual(['1.2']);
  });

  it('keeps a code draft for the open version and opens it again', async () => {
    const backend = createBackend();
    const { openStrategy } = createOpenStrategy();
    const load = openStrategy.load(backend.fetchFunction, 1, 1);
    await backend.answer('1');
    await backend.answer('1/versions/1');
    await load;
    openStrategy.changeCode('edited code');
    const open = openStrategy.openVersion(backend.fetchFunction, 1, 1);
    await backend.answer('1/versions/1');
    await open;

    expect(openStrategy.code).toBe('edited code');
    expect(openStrategy.hasUnsavedCode).toBe(true);
  });
});
