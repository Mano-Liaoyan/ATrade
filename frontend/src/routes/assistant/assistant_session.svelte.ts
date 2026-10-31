// The state of the AI assistant column that all workbench pages share (docs/architecture/assistant.md 25.12): the
// conversation list, the open conversation and its /ws/assistant socket, the log, the model selection and the thinking
// level, the message
// draft, and the Keep and Discard choices of the diff cards and the condition cards. Each page mounts its own AssistantColumn, but the state
// is one module object, so a page change keeps the open conversation and does not close its socket (a closed socket
// stops the run, 25.10).
import { SvelteMap } from 'svelte/reactivity';
import {
  addServerMessage,
  addUserMessage,
  createConversation,
  DEFAULT_THINKING_LEVEL,
  deleteConversation,
  describeThinkingSelect,
  discardStrategyVersion,
  EMPTY_LOG,
  findDefaultSelection,
  isThinkingLevel,
  listConversations,
  listCredentials,
  listProviders,
  openConversationSocket,
  readConversation,
  readConversationLog,
  renameConversation,
  type ConnectionState,
  type Conversation,
  type ConversationLog,
  type ConversationSocket,
  type Credential,
  type DiffItem,
  type LastModel,
  type ModelSelection,
  type Provider,
  type ThinkingLevel,
} from '#lib/assistant';
import { readStoredLayout, writeStoredLayout } from '#lib/foundation/workbench';
import { deleteScreen, keepScreen } from '#lib/screen';

export type DiffChoice = 'kept' | 'discarded';

/** The open strategy of the page. A new conversation records it (25.9). */
export interface OpenStrategy {
  strategyId: number;
  versionNumber: number | null;
}

export interface VersionAddress {
  strategyId: number;
  versionNumber: number;
}

// The title is generated after the run settles (25.8.3), so the list is read again a little later.
const TITLE_READ_DELAY_MILLISECONDS = 1000;
// The browser keeps the open conversation, so a reload opens it again.
const OPEN_CONVERSATION_STORAGE_KEY = 'atrade.assistant-column.conversation';

// The browser keeps the last chosen thinking level for all conversations.
const THINKING_LEVEL_STORAGE_KEY = 'atrade.assistant-column.thinking-level';

function readStoredThinkingLevel(): ThinkingLevel {
  const stored = readStoredLayout(THINKING_LEVEL_STORAGE_KEY);
  return isThinkingLevel(stored) ? stored : DEFAULT_THINKING_LEVEL;
}

function readStoredConversationId(): number | null {
  const stored = readStoredLayout(OPEN_CONVERSATION_STORAGE_KEY);
  return typeof stored === 'number' ? stored : null;
}

function readNowUtc(): string {
  return new Date().toISOString();
}

function findConversationToOpen(
  conversations: readonly Conversation[],
  selectId: number | null,
  opensNewest: boolean,
): number | null {
  if (conversations.some((item) => item.id === selectId)) {
    return selectId;
  }
  return opensNewest ? (conversations[0]?.id ?? null) : null;
}

function readLastModel(item: Conversation | null): LastModel {
  return {
    provider: item?.last_provider ?? null,
    model: item?.last_model ?? null,
    credentialName: item?.last_credential_name ?? null,
  };
}

export class AssistantSession {
  conversations = $state<Conversation[]>([]);
  conversationId = $state<number | null>(null);
  log = $state<ConversationLog>(EMPTY_LOG);
  #socketState = $state<ConnectionState>('connecting');
  // The saved messages are in the log. A message sent before would be lost when the history replaces the log.
  #isHistoryRead = $state(false);
  /** Open only when the socket is open and the saved messages are read, so Send cannot race the history. */
  readonly connection = $derived<ConnectionState>(
    this.#socketState === 'open' && !this.#isHistoryRead ? 'connecting' : this.#socketState,
  );
  providers = $state<Provider[]>([]);
  credentials = $state<Credential[]>([]);
  selection = $state<ModelSelection>({ provider: '', model: '', credentialId: '' });
  /** The last chosen thinking level. A model without it uses the level of `thinking`. */
  thinkingLevel = $state<ThinkingLevel>(readStoredThinkingLevel());
  /** The Thinking select: only the levels of the selected model. */
  readonly thinking = $derived(describeThinkingSelect(this.providers, this.selection, this.thinkingLevel));
  /** The message input. It stays across pages. */
  text = $state('');
  /** The choice of each diff card of the open conversation, by its item ID. */
  readonly diffChoices = new SvelteMap<number, DiffChoice>();
  /** The choice of each screen of the condition cards, by its screen ID. All cards of one screen share it. */
  readonly screenChoices = new SvelteMap<number, DiffChoice>();
  /** The last error, for a page that has no Output tab. Empty when there is none. */
  errorText = $state('');

  readonly conversation = $derived(this.conversations.find((item) => item.id === this.conversationId) ?? null);

  #socket: ConversationSocket | null = null;
  #socketConversationId: number | null = null;
  #titleTimer: ReturnType<typeof setTimeout> | undefined;
  #listReadCount = 0;
  #errorReceiver: ((text: string) => void) | null = null;
  // A diff card on another page asked the strategy page to open this diff.
  #pendingDiff: VersionAddress | null = null;

  /** A page with an Output tab gets the errors. Returns the function that removes the handler. */
  receiveErrors(handler: (text: string) => void): () => void {
    this.#errorReceiver = handler;
    return () => {
      if (this.#errorReceiver === handler) {
        this.#errorReceiver = null;
      }
    };
  }

  reportError(text: string): void {
    if (this.#errorReceiver === null) {
      this.errorText = text;
    } else {
      this.#errorReceiver(text);
    }
  }

  /** Reads the list and keeps the conversation `selectId` (default: the open one, else the stored one) when it is in
   * the list. Else it opens the newest with `opensNewest`, or no conversation. A page that opens does not open the
   * newest: that can be a conversation of another browser tab, and a socket that closes stops its run (25.10). */
  async readConversations(
    selectId: number | null = this.conversationId ?? readStoredConversationId(),
    opensNewest = false,
  ): Promise<void> {
    this.#listReadCount += 1;
    const readCount = this.#listReadCount;
    const result = await listConversations(fetch);
    // An older answer does not change the column.
    if (readCount !== this.#listReadCount) {
      return;
    }
    if (result.kind === 'failed') {
      this.reportError(`Conversations not read: ${result.message}`);
      return;
    }
    this.conversations = result.value;
    this.openConversation(findConversationToOpen(result.value, selectId, opensNewest));
  }

  async readModels(): Promise<void> {
    const [providerResult, credentialResult] = await Promise.all([listProviders(fetch), listCredentials(fetch)]);
    if (providerResult.kind === 'failed') {
      this.reportError(`Providers not read: ${providerResult.message}`);
      return;
    }
    if (credentialResult.kind === 'failed') {
      this.reportError(`Credentials not read: ${credentialResult.message}`);
      return;
    }
    this.providers = providerResult.value.providers;
    this.credentials = credentialResult.value.credentials;
    if (!this.credentials.some((item) => item.id === this.selection.credentialId)) {
      this.selection = findDefaultSelection(this.providers, this.credentials, readLastModel(this.conversation));
    }
  }

  /** One socket for the open conversation. The same conversation keeps its socket while it is open. */
  openConversation(id: number | null): void {
    this.conversationId = id;
    writeStoredLayout(OPEN_CONVERSATION_STORAGE_KEY, id);
    if (id !== null && id === this.#socketConversationId && this.#socketState !== 'closed') {
      return;
    }
    this.#closeSocket();
    this.log = EMPTY_LOG;
    this.diffChoices.clear();
    this.screenChoices.clear();
    if (id === null) {
      return;
    }
    this.#socketState = 'connecting';
    this.#isHistoryRead = false;
    this.#socketConversationId = id;
    void readConversation(fetch, id).then((result) => {
      if (this.#socketConversationId !== id) {
        return;
      }
      this.#isHistoryRead = true;
      if (result.kind === 'failed') {
        this.reportError(`Conversation not read: ${result.message}`);
        return;
      }
      this.log = readConversationLog(result.value.messages, result.value.created_at_utc);
      this.selection = findDefaultSelection(this.providers, this.credentials, readLastModel(result.value));
    });
    const opened = openConversationSocket(id, window.location, {
      onMessage: (message) => {
        if (this.#socket !== opened) {
          return;
        }
        this.log = addServerMessage(this.log, message, readNowUtc());
        if (message.type === 'run_state' && message.state === 'settled') {
          clearTimeout(this.#titleTimer);
          this.#titleTimer = setTimeout(() => void this.readConversations(id), TITLE_READ_DELAY_MILLISECONDS);
        }
      },
      onError: (text) => {
        if (this.#socket === opened) {
          this.reportError(text);
        }
      },
      onConnectionChange: (connected) => {
        if (this.#socket === opened) {
          this.#socketState = connected ? 'open' : 'closed';
        }
      },
    });
    this.#socket = opened;
  }

  #closeSocket(): void {
    clearTimeout(this.#titleTimer);
    const socket = this.#socket;
    this.#socket = null;
    this.#socketConversationId = null;
    socket?.close();
  }

  chooseThinkingLevel(level: ThinkingLevel): void {
    this.thinkingLevel = level;
    writeStoredLayout(THINKING_LEVEL_STORAGE_KEY, level);
  }

  /** Sends the message input. False when nothing was sent. */
  send(): boolean {
    const message = this.text.trim();
    if (message === '' || this.#socket === null) {
      return false;
    }
    this.#socket.send({
      type: 'prompt',
      text: message,
      provider: this.selection.provider,
      model: this.selection.model,
      credential_id: this.selection.credentialId,
      thinking_level: this.thinking.value,
    });
    this.log = addUserMessage(this.log, message, readNowUtc());
    this.text = '';
    return true;
  }

  abort(): void {
    this.#socket?.send({ type: 'abort' });
  }

  async startConversation(openStrategy: OpenStrategy | null): Promise<void> {
    const result = await createConversation(fetch, openStrategy);
    if (result.kind === 'failed') {
      this.reportError(`Conversation not created: ${result.message}`);
      return;
    }
    // A list read that runs at the same time keeps the new conversation.
    this.conversations = [result.value, ...this.conversations];
    this.openConversation(result.value.id);
    await this.readConversations(result.value.id);
  }

  async rename(conversationId: number, title: string): Promise<void> {
    const result = await renameConversation(fetch, conversationId, title);
    if (result.kind === 'failed') {
      this.reportError(`Conversation not renamed: ${result.message}`);
      return;
    }
    await this.readConversations(conversationId);
  }

  async delete(conversationId: number): Promise<void> {
    const error = await deleteConversation(fetch, conversationId);
    if (error !== null) {
      this.reportError(`Conversation not deleted: ${error}`);
      return;
    }
    await this.readConversations(null, true);
  }

  /** Adds the discarded mark to the version of a diff card. False when the discard failed. */
  async discard(item: DiffItem): Promise<boolean> {
    const error = await discardStrategyVersion(fetch, item.strategyId, item.versionNumber);
    if (error !== null) {
      this.reportError(`v${String(item.versionNumber)} not discarded: ${error}`);
      return false;
    }
    this.diffChoices.set(item.id, 'discarded');
    return true;
  }

  /** Keep of a condition card: the AI assistant cannot change the screen after it (25.6). */
  async keepScreen(screenId: number): Promise<void> {
    const error = await keepScreen(fetch, screenId);
    if (error !== null) {
      this.reportError(`Screen not kept: ${error}`);
      return;
    }
    this.screenChoices.set(screenId, 'kept');
  }

  /** Discard of a condition card: deletes the screen (25.6). Old backtests keep their copy of it. */
  async discardScreen(screenId: number): Promise<void> {
    const error = await deleteScreen(fetch, screenId);
    if (error !== null) {
      this.reportError(`Screen not discarded: ${error}`);
      return;
    }
    this.screenChoices.set(screenId, 'discarded');
  }

  /** A diff card on another page asks the strategy page to open the diff after it opens the strategy. */
  requestDiff(address: VersionAddress): void {
    this.#pendingDiff = address;
  }

  /** The version number of the diff that the strategy page must open for this strategy, or null. */
  takeRequestedDiff(strategyId: number): number | null {
    const requested = this.#pendingDiff;
    if (requested?.strategyId !== strategyId) {
      return null;
    }
    this.#pendingDiff = null;
    return requested.versionNumber;
  }
}

export const assistantSession = new AssistantSession();
