// The saved chart indicator set of a page: the read, the saves in order, and a change before the read answer.
import { describe, expect, it } from 'vite-plus/test';
import type { ChartIndicatorSet } from './chart_indicator_set';
import type { ChartPane } from './chart_indicators';
import { ChartIndicatorSetStore } from './chart_indicator_set_store.svelte';

const SMA_PANES: ChartPane[] = [
  { indicators: [{ indicator: 'sma', parameters: { period: 50 }, hidden: false, lines: [{ output: 'value', color: 1, style: 'solid', width: 2 }] }] },
];
const SAVED_SET: ChartIndicatorSet = { panes: SMA_PANES, favorites: ['rsi'] };

interface FakeBackend {
  fetchFunction: typeof fetch;
  savedSets: ChartIndicatorSet[];
  /** Answers the waiting GET. */
  answerRead: () => void;
}

function createBackend({ readStatus = 200, saveStatus = 200 } = {}): FakeBackend {
  const savedSets: ChartIndicatorSet[] = [];
  let answerRead: () => void = () => undefined;
  const fetchFunction: typeof fetch = (_input, init) => {
    if (init?.method === 'PUT') {
      const body = JSON.parse(init.body as string) as ChartIndicatorSet;
      savedSets.push(body);
      const answer = saveStatus === 200 ? body : { detail: 'The database is not reachable.' };
      return Promise.resolve(new Response(JSON.stringify(answer), { status: saveStatus }));
    }
    return new Promise((resolve) => {
      answerRead = () => {
        const answer = readStatus === 200 ? SAVED_SET : { detail: 'Reading failed.' };
        resolve(new Response(JSON.stringify(answer), { status: readStatus }));
      };
    });
  };
  return {
    fetchFunction,
    savedSets,
    answerRead: () => {
      answerRead();
    },
  };
}

async function settle(): Promise<void> {
  for (let index = 0; index < 20; index += 1) {
    await Promise.resolve();
  }
}

describe('ChartIndicatorSetStore', () => {
  it('shows the saved set after the read', async () => {
    const backend = createBackend();
    const store = new ChartIndicatorSetStore();

    const loading = store.load(backend.fetchFunction);
    backend.answerRead();

    expect(await loading).toBe(true);
    expect(store.panes).toEqual(SMA_PANES);
    expect(store.favorites).toEqual(['rsi']);
  });

  it('saves a favorite with the saved panes, also when the favorite changes before the read answer', async () => {
    const backend = createBackend();
    const store = new ChartIndicatorSetStore();

    void store.load(backend.fetchFunction);
    store.toggleFavorite(backend.fetchFunction, 'sma');
    backend.answerRead();
    await settle();

    expect(store.favorites).toEqual(['sma']);
    expect(store.panes).toEqual(SMA_PANES);
    expect(backend.savedSets).toEqual([{ panes: SMA_PANES, favorites: ['sma'] }]);
  });

  it('keeps a pane change before the read answer and saves it with the saved favorites', async () => {
    const backend = createBackend();
    const store = new ChartIndicatorSetStore();
    const emptyPanes: ChartPane[] = [{ indicators: [] }];

    void store.load(backend.fetchFunction);
    store.changePanes(backend.fetchFunction, emptyPanes);
    backend.answerRead();
    await settle();

    expect(store.panes).toEqual(emptyPanes);
    expect(backend.savedSets).toEqual([{ panes: emptyPanes, favorites: ['rsi'] }]);
  });

  it('does not save a favorite when the read fails', async () => {
    const backend = createBackend({ readStatus: 500 });
    const store = new ChartIndicatorSetStore();

    store.toggleFavorite(backend.fetchFunction, 'sma');
    await settle();
    backend.answerRead();
    await settle();

    expect(backend.savedSets).toEqual([]);
    expect(store.errorText).toBe('Reading failed.');
  });

  it('keeps the change and shows the detail text when the save fails', async () => {
    const backend = createBackend({ saveStatus: 500 });
    const store = new ChartIndicatorSetStore();
    void store.load(backend.fetchFunction);
    backend.answerRead();
    await settle();

    store.changePanes(backend.fetchFunction, [{ indicators: [] }]);
    await settle();

    expect(store.panes).toEqual([{ indicators: [] }]);
    expect(store.errorText).toBe('The database is not reachable.');
  });
});
