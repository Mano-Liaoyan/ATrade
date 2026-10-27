// Public entry of foundation/live_socket: a WebSocket that connects again after a close or a missing heartbeat.
// Browsers suspend background tabs in different ways, so the reconnection is our own code (docs/architecture.md section 13).

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

function isHeartbeat(message: unknown): boolean {
  return typeof message === 'object' && message !== null && 'type' in message && message.type === HEARTBEAT_MESSAGE_TYPE;
}

export function buildSocketUrl(path: string, location: { protocol: string; host: string }): string {
  const socketProtocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${socketProtocol}//${location.host}${path}`;
}

/** Opens the socket and keeps it open. Returns a function that closes it for good. */
export function openLiveSocket(options: LiveSocketOptions): () => void {
  const createSocket = options.createSocket ?? createBrowserSocket;
  const heartbeatTimeoutMilliseconds = options.heartbeatTimeoutMilliseconds ?? DEFAULT_HEARTBEAT_TIMEOUT_MILLISECONDS;
  const firstReconnectDelayMilliseconds = options.reconnectDelayMilliseconds ?? DEFAULT_RECONNECT_DELAY_MILLISECONDS;
  let reconnectDelayMilliseconds = firstReconnectDelayMilliseconds;
  let isStopped = false;
  let socket: OpenSocket | null = null;
  let heartbeatTimer: ReturnType<typeof setTimeout> | undefined;
  let reconnectTimer: ReturnType<typeof setTimeout> | undefined;

  function restartHeartbeatTimer(): void {
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
    restartHeartbeatTimer();
    const message: unknown = JSON.parse(text);
    if (!isHeartbeat(message)) {
      options.onMessage(message);
    }
  }

  function connect(): void {
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

  connect();
  return () => {
    isStopped = true;
    clearTimeout(reconnectTimer);
    clearTimeout(heartbeatTimer);
    socket?.close();
  };
}
