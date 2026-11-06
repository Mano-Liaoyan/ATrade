// readOnChange: a read at once, after each socket open, and after each "changed" message; one read at a time.
import { describe, expect, it } from 'vite-plus/test';
import { readOnChange, type LiveSocketOptions } from './index';

const LOCATION = { protocol: 'http:', host: 'localhost' };

interface FakeSocket {
  options: LiveSocketOptions | null;
  isClosed: boolean;
}

function createFakeSocket(): { socket: FakeSocket; openSocket: (options: LiveSocketOptions) => () => void } {
  const socket: FakeSocket = { options: null, isClosed: false };
  return {
    socket,
    openSocket: (options) => {
      socket.options = options;
      return () => {
        socket.isClosed = true;
      };
    },
  };
}

// Lets the pending promise callbacks run.
async function settle(): Promise<void> {
  for (let step = 0; step < 5; step += 1) {
    await Promise.resolve();
  }
}

function createDeferredReads(): { read: () => Promise<number>; finish: () => void; count: () => number } {
  const pending: (() => void)[] = [];
  let readCount = 0;
  return {
    read: () => {
      readCount += 1;
      const value = readCount;
      return new Promise((resolve) => {
        pending.push(() => {
          resolve(value);
        });
      });
    },
    finish: () => {
      pending.shift()?.();
    },
    count: () => readCount,
  };
}

describe('readOnChange', () => {
  it('reads at once and after each changed message, on the socket path', async () => {
    const { socket, openSocket } = createFakeSocket();
    const results: number[] = [];
    let readCount = 0;
    readOnChange({
      socketPath: '/ws/backtests',
      read: () => Promise.resolve((readCount += 1)),
      onResult: (value) => results.push(value),
      location: LOCATION,
      openSocket,
    });
    await settle();
    socket.options?.onMessage({ type: 'changed' });
    await settle();
    socket.options?.onMessage({ type: 'other' });
    await settle();

    expect(socket.options?.url).toBe('ws://localhost/ws/backtests');
    expect(results).toEqual([1, 2]);
  });

  it('reads again after each open, because a change while closed is not known', async () => {
    const { socket, openSocket } = createFakeSocket();
    const connectionStates: boolean[] = [];
    let readCount = 0;
    readOnChange({
      socketPath: '/ws/backtests',
      read: () => Promise.resolve((readCount += 1)),
      onResult: () => undefined,
      onConnectionChange: (isConnected) => connectionStates.push(isConnected),
      location: LOCATION,
      openSocket,
    });
    await settle();
    socket.options?.onConnectionChange(true);
    await settle();
    socket.options?.onConnectionChange(false);
    socket.options?.onConnectionChange(true);
    await settle();

    expect(readCount).toBe(3);
    expect(connectionStates).toEqual([true, false, true]);
  });

  it('runs one read at a time and reads once more after changes during a read', async () => {
    const { socket, openSocket } = createFakeSocket();
    const reads = createDeferredReads();
    const results: number[] = [];
    readOnChange({ socketPath: '/ws/x', read: reads.read, onResult: (value) => results.push(value), location: LOCATION, openSocket });
    socket.options?.onMessage({ type: 'changed' });
    socket.options?.onMessage({ type: 'changed' });
    expect(reads.count()).toBe(1);

    reads.finish();
    await settle();
    expect(reads.count()).toBe(2);
    reads.finish();
    await settle();

    expect(results).toEqual([1, 2]);
    expect(reads.count()).toBe(2);
  });

  it('reads again after a read that rejects', async () => {
    const { socket, openSocket } = createFakeSocket();
    const results: number[] = [];
    let readCount = 0;
    // readNow keeps the rejection for the browser console. The test runner must not count it as an error.
    const runnerListeners = process.listeners('unhandledRejection');
    const rejections: unknown[] = [];
    process.removeAllListeners('unhandledRejection');
    process.on('unhandledRejection', (reason) => rejections.push(reason));
    readOnChange({
      socketPath: '/ws/x',
      read: () => {
        readCount += 1;
        return readCount === 1 ? Promise.reject(new Error('Body read failed.')) : Promise.resolve(readCount);
      },
      onResult: (value) => results.push(value),
      location: LOCATION,
      openSocket,
    });
    await settle();
    socket.options?.onMessage({ type: 'changed' });
    await settle();
    await new Promise((resolve) => setTimeout(resolve));
    process.removeAllListeners('unhandledRejection');
    runnerListeners.forEach((listener) => process.on('unhandledRejection', listener));

    expect(results).toEqual([2]);
    expect(rejections).toHaveLength(1);
  });

  it('closes the socket at stop and gives no result after it', async () => {
    const { socket, openSocket } = createFakeSocket();
    const reads = createDeferredReads();
    const results: number[] = [];
    const stop = readOnChange({ socketPath: '/ws/x', read: reads.read, onResult: (value) => results.push(value), location: LOCATION, openSocket });
    stop();
    reads.finish();
    await settle();

    expect(socket.isClosed).toBe(true);
    expect(results).toEqual([]);
  });
});
