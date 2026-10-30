// The /ws/assistant socket of one conversation (docs/architecture/assistant.md 25.10). The browser sends `prompt` and
// `abort`, and the server streams the run. The socket does not connect again after a close: `web` stops a run when
// the browser leaves, so a new socket cannot continue it.
import type { components } from '#lib/api';
import { buildSocketUrl, readSocketMessage } from '#lib/foundation/live_socket';
import type { ServerMessage } from './conversation_log';

type PromptMessage = components['schemas']['PromptMessage'];
type AbortMessage = components['schemas']['AbortMessage'];
type AssistantErrorMessage = components['schemas']['AssistantErrorMessage'];

const SERVER_MESSAGE_TYPES: (ServerMessage | AssistantErrorMessage)['type'][] = [
  'message_delta',
  'message_end',
  'run_state',
  'tool_step',
  'strategy_version_saved',
  'backtest_finished',
  'error',
];

export interface ConversationSocketEvents {
  onMessage: (message: ServerMessage) => void;
  onError: (message: string) => void;
  onConnectionChange: (isConnected: boolean) => void;
}

export interface ConversationSocket {
  send: (message: PromptMessage | AbortMessage) => void;
  close: () => void;
}

export function openConversationSocket(
  conversationId: number,
  location: { protocol: string; host: string },
  events: ConversationSocketEvents,
): ConversationSocket {
  const socket = new WebSocket(buildSocketUrl(`/ws/assistant?conversation_id=${String(conversationId)}`, location));
  let isClosed = false;
  // After close(), the page has a new socket: the events of this one do not change the page.
  socket.addEventListener('open', () => {
    if (!isClosed) {
      events.onConnectionChange(true);
    }
  });
  socket.addEventListener('close', () => {
    if (!isClosed) {
      events.onConnectionChange(false);
    }
  });
  socket.addEventListener('message', (event: MessageEvent<unknown>) => {
    if (isClosed || typeof event.data !== 'string') {
      return;
    }
    const message = readSocketMessage<ServerMessage | AssistantErrorMessage>(JSON.parse(event.data), SERVER_MESSAGE_TYPES);
    if (message === null) {
      return;
    }
    if (message.type === 'error') {
      events.onError(message.message);
    } else {
      events.onMessage(message);
    }
  });
  return {
    send: (message) => {
      socket.send(JSON.stringify(message));
    },
    close: () => {
      isClosed = true;
      socket.close();
    },
  };
}
