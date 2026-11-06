// The diff tab: a delayed read that a strategy change or a newer open replaced shows nothing.
import { describe, expect, it } from 'vite-plus/test';
import { AssistantDiff } from './assistant_diff.svelte';

interface FakeBackend {
  fetchFunction: typeof fetch;
  /** Answers the waiting reads of a strategy. */
  answer: (strategyId: number) => void;
}

function createBackend(): FakeBackend {
  const waiting: { path: string; resolve: (response: Response) => void }[] = [];
  return {
    fetchFunction: (input) =>
      new Promise((resolve) => {
        waiting.push({ path: input as string, resolve });
      }),
    answer: (strategyId) => {
      for (const read of waiting.filter((item) => item.path.startsWith(`/api/strategies/${String(strategyId)}/`))) {
        read.resolve(new Response(JSON.stringify({ code: read.path }), { status: 200 }));
      }
    },
  };
}

describe('AssistantDiff', () => {
  it('shows the versions of the diff', async () => {
    const backend = createBackend();
    const diff = new AssistantDiff();
    const open = diff.open(backend.fetchFunction, 1, 3);
    backend.answer(1);

    expect(await open).toBeNull();
    expect(diff.isSelected).toBe(true);
    expect(diff.diff?.versionNumber).toBe(3);
  });

  it('drops a late read after close', async () => {
    const backend = createBackend();
    const diff = new AssistantDiff();
    const open = diff.open(backend.fetchFunction, 1, 3);
    diff.close();
    backend.answer(1);

    expect(await open).toBeNull();
    expect(diff.diff).toBeNull();
    expect(diff.isSelected).toBe(false);
  });

  it('drops an older read that ends after a newer open', async () => {
    const backend = createBackend();
    const diff = new AssistantDiff();
    const firstOpen = diff.open(backend.fetchFunction, 1, 3);
    const secondOpen = diff.open(backend.fetchFunction, 2, 5);
    backend.answer(2);
    await secondOpen;
    backend.answer(1);
    await firstOpen;

    expect(diff.diff?.versionNumber).toBe(5);
    expect(diff.diff?.secondCode).toBe('/api/strategies/2/versions/5');
  });
});
