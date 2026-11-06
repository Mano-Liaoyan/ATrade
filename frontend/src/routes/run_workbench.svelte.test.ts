// The shared state of the run pages: the list, the open-newest navigation, the two detail reads, and the New dialog.
import { flushSync } from 'svelte';
import { beforeEach, describe, expect, it, vi } from 'vite-plus/test';
import type { RequestResult } from '#lib/foundation/http_request';
import { RunWorkbench, type RunWorkbenchOptions } from './run_workbench.svelte';
import { navigating, page } from './run_workbench_fake_app.svelte';

const { goto, sockets } = vi.hoisted(() => ({
  goto: vi.fn(),
  sockets: [] as { request: () => void; connect: (isConnected: boolean) => void; isClosed: boolean }[],
}));

vi.mock('$app/navigation', () => ({ goto }));
vi.mock('$app/state', () => import('./run_workbench_fake_app.svelte'));
// One read at the start and one read for each request. A closed socket gives no result, like readOnChange.
vi.mock('#lib/foundation/live_socket', () => ({
  readOnChange: (options: {
    read: () => Promise<unknown>;
    onResult: (value: unknown) => void;
    onConnectionChange?: (isConnected: boolean) => void;
  }) => {
    const socket = {
      isClosed: false,
      request: () => {
        void options.read().then((value) => {
          if (!socket.isClosed) {
            options.onResult(value);
          }
        });
      },
      connect: (isConnected: boolean) => options.onConnectionChange?.(isConnected),
    };
    sockets.push(socket);
    socket.request();
    return () => {
      socket.isClosed = true;
    };
  },
}));

interface Run {
  id: number;
  status: string;
}

function ok<T>(value: T): RequestResult<T> {
  return { kind: 'ok', value };
}

let openId = $state<number | null>(null);
let items: RequestResult<Run[]> = ok([]);
let stops: (() => void)[] = [];

function start(options: Partial<RunWorkbenchOptions<Run, Run>> = {}): RunWorkbench<Run, Run> {
  let workbench: RunWorkbench<Run, Run> | undefined;
  stops.push(
    $effect.root(() => {
      workbench = new RunWorkbench<Run, Run>({
        socketPath: '/ws/runs',
        list: () => Promise.resolve(items),
        readDetail: (id) => Promise.resolve(ok({ id, status: 'running' })),
        href: (id) => `/runs/${String(id)}`,
        openId: () => openId,
        ...options,
      });
    }),
  );
  flushSync();
  return workbench as RunWorkbench<Run, Run>;
}

async function settle(): Promise<void> {
  await new Promise((resolve) => {
    setTimeout(resolve);
  });
  flushSync();
}

beforeEach(() => {
  stops.forEach((stop) => {
    stop();
  });
  stops = [];
  sockets.length = 0;
  goto.mockClear();
  openId = null;
  items = ok([]);
  navigating.to = null;
  page.url.hash = '';
});

describe('RunWorkbench list', () => {
  it('shows the list of each read', async () => {
    items = ok([{ id: 1, status: 'running' }]);
    const workbench = start();
    expect(workbench.isListRead).toBe(false);
    await settle();
    expect(workbench.isListRead).toBe(true);
    expect(workbench.items).toEqual([{ id: 1, status: 'running' }]);
  });

  it('keeps the last list and shows the message of a failed read', async () => {
    items = ok([{ id: 1, status: 'running' }]);
    const workbench = start();
    await settle();
    items = { kind: 'failed', message: 'Not read' };
    sockets[0]?.request();
    await settle();
    expect(workbench.listMessage).toBe('Not read');
    expect(workbench.items).toHaveLength(1);
  });

  it('follows the socket connection state', () => {
    const workbench = start();
    sockets[0]?.connect(true);
    expect(workbench.isConnected).toBe(true);
  });
});

describe('RunWorkbench open newest', () => {
  it('opens the highest id for any list order, and keeps the page state', async () => {
    items = ok([
      { id: 2, status: 'running' },
      { id: 9, status: 'running' },
      { id: 5, status: 'running' },
    ]);
    start();
    await settle();
    expect(goto).toHaveBeenCalledExactlyOnceWith('/runs/9', { replace: true, reset: false });
  });

  it('does not navigate from an address with an id', async () => {
    items = ok([{ id: 9, status: 'running' }]);
    openId = 2;
    start();
    await settle();
    expect(goto).not.toHaveBeenCalled();
  });

  it('waits for a navigation that runs', async () => {
    items = ok([{ id: 9, status: 'running' }]);
    navigating.to = {};
    start();
    await settle();
    expect(goto).not.toHaveBeenCalled();
    navigating.to = null;
    flushSync();
    expect(goto).toHaveBeenCalledOnce();
  });
});

describe('RunWorkbench detail, read on a list row change', () => {
  it('reads again when the open list row changes, not for other rows', async () => {
    openId = 1;
    const readDetail = vi.fn((id: number) => Promise.resolve(ok({ id, status: 'running' })));
    const workbench = start({ readDetail });
    await settle();
    expect(readDetail).toHaveBeenCalledOnce();
    expect(workbench.detail).toEqual({ id: 1, status: 'running' });

    items = ok([{ id: 1, status: 'running' }]);
    sockets[0]?.request();
    await settle();
    expect(readDetail).toHaveBeenCalledTimes(2);

    items = ok([
      { id: 1, status: 'running' },
      { id: 2, status: 'running' },
    ]);
    sockets[0]?.request();
    await settle();
    expect(readDetail).toHaveBeenCalledTimes(2);

    items = ok([{ id: 1, status: 'finished' }]);
    sockets[0]?.request();
    await settle();
    expect(readDetail).toHaveBeenCalledTimes(3);
  });

  it('does not read a final detail again', async () => {
    openId = 1;
    const readDetail = vi.fn((id: number) => Promise.resolve(ok({ id, status: 'finished' })));
    const workbench = start({ readDetail, isFinal: (detail, id) => detail.id === id && detail.status === 'finished' });
    await settle();
    expect(readDetail).toHaveBeenCalledOnce();
    expect(workbench.detail?.status).toBe('finished');

    items = ok([{ id: 1, status: 'finished' }]);
    sockets[0]?.request();
    await settle();
    expect(readDetail).toHaveBeenCalledOnce();
  });

  it('ignores the answer of a run that is not open any more', async () => {
    openId = 1;
    const answers = new Map<number, (result: RequestResult<Run>) => void>();
    const readDetail = (id: number): Promise<RequestResult<Run>> =>
      new Promise((resolve) => {
        answers.set(id, resolve);
      });
    const workbench = start({ readDetail });
    openId = 2;
    flushSync();
    answers.get(2)?.(ok({ id: 2, status: 'running' }));
    await settle();
    answers.get(1)?.(ok({ id: 1, status: 'running' }));
    await settle();
    expect(workbench.detail?.id).toBe(2);
  });

  it('shows the message of a failed read', async () => {
    openId = 1;
    const workbench = start({ readDetail: () => Promise.resolve({ kind: 'failed', message: 'Not read' }) });
    await settle();
    expect(workbench.detailMessage).toBe('Not read');
  });
});

describe('RunWorkbench detail, read on each socket change', () => {
  it('gives a new value only after a change of the data', async () => {
    openId = 1;
    let status = 'running';
    const workbench = start({
      readsDetailOnChange: true,
      readDetail: (id) => Promise.resolve(ok({ id, status })),
    });
    const detailSocket = sockets[1];
    await settle();
    const first = workbench.detail;
    expect(first).toEqual({ id: 1, status: 'running' });

    detailSocket?.request();
    await settle();
    expect(workbench.detail).toBe(first);

    status = 'stopped';
    detailSocket?.request();
    await settle();
    expect(workbench.detail).toEqual({ id: 1, status: 'stopped' });
  });

  it('closes the socket of the old run', async () => {
    openId = 1;
    start({ readsDetailOnChange: true });
    await settle();
    openId = 2;
    flushSync();
    expect(sockets[1]?.isClosed).toBe(true);
    expect(sockets[2]?.isClosed).toBe(false);
  });
});

describe('RunWorkbench New dialog', () => {
  it('opens on the hash, and a close removes the hash', () => {
    page.url.hash = '#start-run';
    const workbench = start({ startHash: '#start-run' });
    expect(workbench.isStartDialogOpen).toBe(true);

    workbench.changeStartDialog(false);
    expect(workbench.isStartDialogOpen).toBe(false);
    expect(goto).toHaveBeenCalledExactlyOnceWith('/runs', { replace: true, reset: false });
  });

  it('does not navigate at a close without the hash', () => {
    const workbench = start({ startHash: '#start-run' });
    workbench.isStartDialogOpen = true;
    workbench.changeStartDialog(false);
    expect(goto).not.toHaveBeenCalled();
  });
});
