// Public entry of foundation/live_socket: a WebSocket that connects again after a close or a missing heartbeat.
// Browsers suspend background tabs in different ways, so the reconnection is our own code (docs/architecture.md section 13).
import type { components } from '#lib/api';
import { readSocketMessage } from './socket_message';

export { readSocketMessage } from './socket_message';

type HeartbeatMessage = components['schemas']['HeartbeatMessage'];

export interface SocketEvents {
  onOpen: () => void;
  onText: (text: string) => void;
  onClose: () => void;
}

export interface OpenSocket {
  close: () => void;
}

export interface LiveSocketOptions {
  url: string;
  onMessage: (message: unknown) => void;
  onConnectionChange: (isConnected: boolean) => void;
  createSocket?: (url: string, events: SocketEvents) => OpenSocket;
  // Calls onVisible each time the page becomes visible. Returns a function that stops the watch.
  watchPageVisible?: (onVisible: () => void) => () => void;
  heartbeatTimeoutMilliseconds?: number;
  reconnectDelayMilliseconds?: number;
}

// The server sends a heartbeat every 10 seconds. Two missing heartbeats and a margin mean a dead connection.
const DEFAULT_HEARTBEAT_TIMEOUT_MILLISECONDS = 25_000;
const DEFAULT_RECONNECT_DELAY_MILLISECONDS = 1_000;
const MAXIMUM_RECONNECT_DELAY_MILLISECONDS = 10_000;
const RECONNECT_DELAY_FACTOR = 2;
const HEARTBEAT_MESSAGE_TYPE = 'heartbeat';

function createBrowserSocket(url: string, events: SocketEvents): OpenSocket {
  const socket = new WebSocket(url);
  socket.addEventListener('open', () => {
    events.onOpen();
  });
  socket.addEventListener('message', (event: MessageEvent<unknown>) => {
    if (typeof event.data === 'string') {
      events.onText(event.data);
    }
  });
  socket.addEventListener('close', () => {
    events.onClose();
  });
  // The browser fires "close" after "error", so the reconnection starts there.
  socket.addEventListener('error', () => {
    socket.close();
  });
  return socket;
}

function watchDocumentVisible(onVisible: () => void): () => void {
  function receiveVisibilityChange(): void {
    if (document.visibilityState === 'visible') {
      onVisible();
    }
  }
  document.addEventListener('visibilitychange', receiveVisibilityChange);
  return () => {
    document.removeEventListener('visibilitychange', receiveVisibilityChange);
  };
}

function isHeartbeat(message: unknown): boolean {
  return readSocketMessage<HeartbeatMessage>(message, [HEARTBEAT_MESSAGE_TYPE]) !== null;
}

export function buildSocketUrl(path: string, location: { protocol: string; host: string }): string {
  const socketProtocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${socketProtocol}//${location.host}${path}`;
}

/** Opens the socket and keeps it open. Returns a function that closes it for good. */
export function openLiveSocket(options: LiveSocketOptions): () => void {
  const createSocket = options.createSocket ?? createBrowserSocket;
  const watchPageVisible = options.watchPageVisible ?? watchDocumentVisible;
  const heartbeatTimeoutMilliseconds = options.heartbeatTimeoutMilliseconds ?? DEFAULT_HEARTBEAT_TIMEOUT_MILLISECONDS;
  const firstReconnectDelayMilliseconds = options.reconnectDelayMilliseconds ?? DEFAULT_RECONNECT_DELAY_MILLISECONDS;
  let reconnectDelayMilliseconds = firstReconnectDelayMilliseconds;
  let isStopped = false;
  let socket: OpenSocket | null = null;
  let heartbeatTimer: ReturnType<typeof setTimeout> | undefined;
  let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
  // A background tab can delay the timers for a long time, so the time of the last message is kept as well.
  let lastMessageAtMilliseconds = Date.now();

  function restartHeartbeatTimer(): void {
    lastMessageAtMilliseconds = Date.now();
    clearTimeout(heartbeatTimer);
    heartbeatTimer = setTimeout(() => socket?.close(), heartbeatTimeoutMilliseconds);
  }

  function scheduleReconnect(): void {
    clearTimeout(heartbeatTimer);
    options.onConnectionChange(false);
    if (isStopped) {
      return;
    }
    reconnectTimer = setTimeout(connect, reconnectDelayMilliseconds);
    reconnectDelayMilliseconds = Math.min(
      reconnectDelayMilliseconds * RECONNECT_DELAY_FACTOR,
      MAXIMUM_RECONNECT_DELAY_MILLISECONDS,
    );
  }

  function receive(text: string): void {
    // A closing socket can still fire a message event after stop.
    if (isStopped) {
      return;
    }
    restartHeartbeatTimer();
    const message: unknown = JSON.parse(text);
    if (!isHeartbeat(message)) {
      options.onMessage(message);
    }
  }

  function connect(): void {
    // A new socket gets the full heartbeat timeout to open and to send its first message.
    lastMessageAtMilliseconds = Date.now();
    let newSocket: OpenSocket | null = null;
    newSocket = createSocket(options.url, {
      onOpen: () => {
        reconnectDelayMilliseconds = firstReconnectDelayMilliseconds;
        options.onConnectionChange(true);
        restartHeartbeatTimer();
      },
      onText: receive,
      onClose: () => {
        // A replaced socket can still report a close. Only the current socket counts.
        if (socket === newSocket) {
          socket = null;
          scheduleReconnect();
        }
      },
    });
    socket = newSocket;
  }

  // When a background tab becomes visible, a dead connection must not wait for timers that the browser delayed.
  function checkAfterPageVisible(): void {
    if (socket === null) {
      clearTimeout(reconnectTimer);
      reconnectDelayMilliseconds = firstReconnectDelayMilliseconds;
      connect();
      return;
    }
    if (Date.now() - lastMessageAtMilliseconds >= heartbeatTimeoutMilliseconds) {
      socket.close();
      clearTimeout(reconnectTimer);
      connect();
    }
  }

  connect();
  const stopWatchingPageVisible = watchPageVisible(checkAfterPageVisible);
  return () => {
    isStopped = true;
    stopWatchingPageVisible();
    clearTimeout(reconnectTimer);
    clearTimeout(heartbeatTimer);
    socket?.close();
  };
}
