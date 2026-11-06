// Reads the data of a page again after each change that a change socket of the backend pushes (foundation/table_changes,
// docs/architecture.md section 13 "Live updates"). The socket sends only {"type": "changed"}; the data comes over HTTP.
// Nothing reads on a timer.
import type { components } from '#lib/api';
import { buildSocketUrl, openLiveSocket, type LiveSocketOptions } from './live_socket';
import { readSocketMessage } from './socket_message';

type ChangedMessage = components['schemas']['ChangedMessage'];

export interface ReadOnChangeOptions<T> {
  /** The /ws/ path of the change socket, for example "/ws/backtests". */
  socketPath: string;
  read: () => Promise<T>;
  onResult: (value: T) => void;
  onConnectionChange?: (isConnected: boolean) => void;
  location?: { protocol: string; host: string };
  openSocket?: (options: LiveSocketOptions) => () => void;
}

/**
 * Calls `read` at once, after each open of the socket (a change while it was closed is not known), and after each
 * "changed" message. One read runs at a time: changes during a read give one more read after it. The returned function
 * closes the socket, and no result reaches `onResult` after it.
 */
export function readOnChange<T>(options: ReadOnChangeOptions<T>): () => void {
  const openSocket = options.openSocket ?? openLiveSocket;
  let isStopped = false;
  let isReading = false;
  // Counts the read requests, so that a request during a read gives one more read.
  let requestCount = 0;

  async function readNow(): Promise<void> {
    requestCount += 1;
    if (isReading) {
      return;
    }
    isReading = true;
    let readRequestCount = 0;
    while (readRequestCount !== requestCount && !isStopped) {
      readRequestCount = requestCount;
      try {
        const value = await options.read();
        if (!isStopped) {
          options.onResult(value);
        }
      } catch (error) {
        // An error must not stop the live updates: the next change reads again.
        console.error(error);
      }
    }
    isReading = false;
  }

  void readNow();
  const closeSocket = openSocket({
    url: buildSocketUrl(options.socketPath, options.location ?? window.location),
    onMessage: (message) => {
      if (readSocketMessage<ChangedMessage>(message, ['changed']) !== null) {
        void readNow();
      }
    },
    onConnectionChange: (isConnected) => {
      if (isConnected) {
        void readNow();
      }
      options.onConnectionChange?.(isConnected);
    },
  });
  return () => {
    isStopped = true;
    closeSocket();
  };
}
