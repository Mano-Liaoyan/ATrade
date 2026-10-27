// Code completion and live type errors: the editor's language server client (docs/architecture/strategy.md section 9.4).
// The backend starts 1 basedpyright process for each WebSocket connection and stops it when the connection closes.
import type { Extension } from '@codemirror/state';
import { LSPClient, languageServerExtensions, type Transport } from '@codemirror/lsp-client';

export const STRATEGY_LANGUAGE_SERVER_PATH = '/ws/strategy-language-server';
// The editor has 1 file. basedpyright needs a file URI. The file does not exist on the server.
export const STRATEGY_DOCUMENT_URI = 'file:///atrade/strategy.py';
const STRATEGY_ROOT_URI = 'file:///atrade';
// The first request includes the analysis of NautilusTrader. It takes longer than the client default of 3 seconds.
const REQUEST_TIMEOUT_MILLISECONDS = 15_000;

/** The part of a browser WebSocket that the transport uses. */
export interface LanguageServerSocket extends EventTarget {
  send(message: string): void;
}

export interface LanguageServerConnection {
  editorExtension: Extension;
  disconnect: () => void;
}

export function readLanguageServerUrl(location: Pick<Location, 'protocol' | 'host'>): string {
  const scheme = location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${scheme}//${location.host}${STRATEGY_LANGUAGE_SERVER_PATH}`;
}

export function connectLanguageServerTransport(socket: LanguageServerSocket): Promise<Transport> {
  const handlers = new Set<(message: string) => void>();
  socket.addEventListener('message', (event) => {
    const { data } = event as MessageEvent<unknown>;
    if (typeof data !== 'string') {
      return;
    }
    for (const handler of handlers) {
      handler(data);
    }
  });
  const transport: Transport = {
    send: (message) => {
      socket.send(message);
    },
    subscribe: (handler) => {
      handlers.add(handler);
    },
    unsubscribe: (handler) => {
      handlers.delete(handler);
    },
  };
  return new Promise((resolve, reject) => {
    const failToOpen = (): void => {
      reject(new Error('The language server connection did not open.'));
    };
    socket.addEventListener('open', () => {
      socket.removeEventListener('close', failToOpen);
      resolve(transport);
    });
    socket.addEventListener('close', failToOpen, { once: true });
  });
}

/**
 * Opens a WebSocket to the language server and returns the editor extension. The editor works without completion
 * while the connection opens or when it fails.
 */
export function connectStrategyLanguageServer(location: Pick<Location, 'protocol' | 'host'>): LanguageServerConnection {
  const client = new LSPClient({
    rootUri: STRATEGY_ROOT_URI,
    timeout: REQUEST_TIMEOUT_MILLISECONDS,
    extensions: languageServerExtensions(),
  });
  const socket = new WebSocket(readLanguageServerUrl(location));
  connectLanguageServerTransport(socket).then(
    (transport) => {
      client.connect(transport);
    },
    () => {
      // No completion without the backend. The save checks still run on the server.
    },
  );
  return {
    editorExtension: client.plugin(STRATEGY_DOCUMENT_URI, 'python'),
    disconnect: () => {
      client.disconnect();
      socket.close();
    },
  };
}
