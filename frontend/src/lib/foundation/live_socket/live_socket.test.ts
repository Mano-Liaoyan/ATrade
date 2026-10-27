// A WebSocket that connects again after a close and after a missing heartbeat, with a fake socket and fake timers.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vite-plus/test';
import { buildSocketUrl, openLiveSocket, type OpenSocket, type SocketEvents } from './index';

class FakeSocket implements OpenSocket {
  isClosed = false;

  constructor(
    readonly url: string,
    readonly events: SocketEvents,
  ) {}

  open(): void {
    this.events.onOpen();
  }

  close(): void {
    this.isClosed = true;
    this.events.onClose();
  }

  receive(message: unknown): void {
    this.events.onText(JSON.stringify(message));
  }
}

function startSocket() {
  const sockets: FakeSocket[] = [];
  const visibleListeners: (() => void)[] = [];
  const messages: unknown[] = [];
  const connectionStates: boolean[] = [];
  const stop = openLiveSocket({
    url: 'ws://test/ws/paper-trading',
    onMessage: (message) => messages.push(message),
    onConnectionChange: (isConnected) => connectionStates.push(isConnected),
    createSocket: (url, events) => {
      const socket = new FakeSocket(url, events);
      sockets.push(socket);
      return socket;
    },
    watchPageVisible: (onVisible) => {
      visibleListeners.push(onVisible);
      return () => visibleListeners.splice(visibleListeners.indexOf(onVisible), 1);
    },
    heartbeatTimeoutMilliseconds: 1000,
    reconnectDelayMilliseconds: 100,
  });
  // A background tab can stop the timers. The page becomes visible again with its timers not run.
  function showPageAfter(milliseconds: number): void {
    vi.setSystemTime(Date.now() + milliseconds);
    for (const onVisible of [...visibleListeners]) {
      onVisible();
    }
  }
  return { sockets, messages, connectionStates, stop, showPageAfter, visibleListeners };
}

function latestSocket(sockets: FakeSocket[]): FakeSocket {
  const socket = sockets.at(-1);
  if (socket === undefined) {
    throw new Error('No socket was created.');
  }
  return socket;
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe('openLiveSocket', () => {
  it('passes messages on and leaves out heartbeats', () => {
    const { sockets, messages, connectionStates } = startSocket();
    const socket = latestSocket(sockets);
    socket.open();

    socket.receive({ type: 'heartbeat' });
    socket.receive({ type: 'account', balance: null });

    expect(messages).toEqual([{ type: 'account', balance: null }]);
    expect(connectionStates).toEqual([true]);
  });

  it('connects again after the server closes the socket', () => {
    const { sockets, connectionStates } = startSocket();
    latestSocket(sockets).open();

    latestSocket(sockets).close();
    vi.advanceTimersByTime(100);

    expect(sockets).toHaveLength(2);
    expect(connectionStates).toEqual([true, false]);
  });

  it('closes and connects again when no message arrives within the heartbeat timeout', () => {
    const { sockets } = startSocket();
    const firstSocket = latestSocket(sockets);
    firstSocket.open();

    vi.advanceTimersByTime(900);
    firstSocket.receive({ type: 'heartbeat' });
    vi.advanceTimersByTime(900);
    expect(firstSocket.isClosed).toBe(false);

    vi.advanceTimersByTime(200);
    expect(firstSocket.isClosed).toBe(true);
    vi.advanceTimersByTime(100);
    expect(sockets).toHaveLength(2);
  });

  it('waits longer after each failed connection, up to a maximum', () => {
    const { sockets } = startSocket();

    latestSocket(sockets).close();
    vi.advanceTimersByTime(100);
    expect(sockets).toHaveLength(2);

    latestSocket(sockets).close();
    vi.advanceTimersByTime(100);
    expect(sockets).toHaveLength(2);
    vi.advanceTimersByTime(100);
    expect(sockets).toHaveLength(3);
  });

  it('does not connect again after stop', () => {
    const { sockets, stop } = startSocket();
    latestSocket(sockets).open();

    stop();
    vi.advanceTimersByTime(10_000);

    expect(sockets).toHaveLength(1);
    expect(latestSocket(sockets).isClosed).toBe(true);
  });

  it('does not pass on a message that arrives after stop', () => {
    const { sockets, messages, stop } = startSocket();
    const socket = latestSocket(sockets);
    socket.open();

    stop();
    // A closing browser socket can still fire a message event.
    socket.receive({ type: 'bar', close: 123 });

    expect(messages).toEqual([]);
  });
});

describe('buildSocketUrl', () => {
  it('uses wss for an https page and ws for an http page', () => {
    expect(buildSocketUrl('/ws/paper-trading', { protocol: 'https:', host: 'atrade.example' })).toBe(
      'wss://atrade.example/ws/paper-trading',
    );
    expect(buildSocketUrl('/ws/paper-trading', { protocol: 'http:', host: '127.0.0.1:4173' })).toBe(
      'ws://127.0.0.1:4173/ws/paper-trading',
    );
  });

  it('connects again at once when a background tab becomes visible after the heartbeat timeout', () => {
    const { sockets, showPageAfter } = startSocket();
    const firstSocket = latestSocket(sockets);
    firstSocket.open();

    showPageAfter(5000);

    expect(firstSocket.isClosed).toBe(true);
    expect(sockets).toHaveLength(2);
  });

  it('keeps a socket with recent messages when the page becomes visible', () => {
    const { sockets, showPageAfter } = startSocket();
    latestSocket(sockets).open();

    showPageAfter(500);

    expect(sockets).toHaveLength(1);
    expect(latestSocket(sockets).isClosed).toBe(false);
  });

  it('stops the reconnection delay when the page becomes visible', () => {
    const { sockets, showPageAfter } = startSocket();
    latestSocket(sockets).close();
    latestSocket(sockets).close();
    expect(sockets).toHaveLength(1);

    showPageAfter(0);

    expect(sockets).toHaveLength(2);
  });

  it('stops watching the page visibility after stop', () => {
    const { stop, visibleListeners } = startSocket();

    stop();

    expect(visibleListeners).toHaveLength(0);
  });
});
