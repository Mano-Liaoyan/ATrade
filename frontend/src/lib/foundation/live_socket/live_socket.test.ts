// A WebSocket that connects again after a close and after a missing heartbeat, with a fake socket and fake timers.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
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
    heartbeatTimeoutMilliseconds: 1000,
    reconnectDelayMilliseconds: 100,
  });
  return { sockets, messages, connectionStates, stop };
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
});
