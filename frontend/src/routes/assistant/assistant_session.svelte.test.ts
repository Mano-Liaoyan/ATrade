// The AI assistant session: the title read after a run, and send() with a run or without a credential.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vite-plus/test';
import { AssistantSession } from './assistant_session.svelte';

const CONVERSATION_ID = 7;
const OTHER_CONVERSATION_ID = 8;
const READ_DELAY_MILLISECONDS = 1000;
const READ_LIMIT = 125;

class FakeWebSocket extends EventTarget {
  static opened: FakeWebSocket | null = null;
  readonly sent: string[] = [];

  constructor() {
    super();
    FakeWebSocket.opened = this;
  }

  send(text: string): void {
    this.sent.push(text);
  }

  close(): void {
    this.dispatchEvent(new Event('close'));
  }

  receive(message: unknown): void {
    // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the MessageEvent option.
    this.dispatchEvent(new MessageEvent('message', { data: JSON.stringify(message) }));
  }
}

function fakeSocket(): FakeWebSocket {
  if (FakeWebSocket.opened === null) {
    throw new Error('No socket is open.');
  }
  return FakeWebSocket.opened;
}

let titleState: string;
let title: string;
let listReadCount: number;

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200, headers: { 'content-type': 'application/json' } });
}

function fakeFetch(input: RequestInfo | URL): Promise<Response> {
  const conversation = { id: CONVERSATION_ID, title, title_state: titleState, created_at_utc: '2026-01-02T03:04:05Z' };
  if ((input as string).endsWith('/conversations')) {
    listReadCount += 1;
    return Promise.resolve(jsonResponse({ conversations: [conversation] }));
  }
  return Promise.resolve(jsonResponse({ ...conversation, messages: [] }));
}

async function openSession(): Promise<AssistantSession> {
  const session = new AssistantSession();
  await session.readConversations(CONVERSATION_ID);
  fakeSocket().dispatchEvent(new Event('open'));
  await vi.advanceTimersByTimeAsync(0);
  listReadCount = 0;
  return session;
}

beforeEach(() => {
  vi.useFakeTimers();
  titleState = 'new';
  title = 'New conversation';
  listReadCount = 0;
  FakeWebSocket.opened = null;
  vi.stubGlobal('fetch', fakeFetch);
  vi.stubGlobal('WebSocket', FakeWebSocket);
  vi.stubGlobal('window', { location: { protocol: 'http:', host: 'localhost' } });
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('the title read after a run', () => {
  it('reads the list once when the title is not in generation', async () => {
    const session = await openSession();
    fakeSocket().receive({ type: 'run_state', state: 'settled' });
    titleState = 'generated';
    title = 'Moving averages';

    await vi.advanceTimersByTimeAsync(5 * READ_DELAY_MILLISECONDS);

    expect(listReadCount).toBe(1);
    expect(session.conversation?.title).toBe('Moving averages');
  });

  it('reads the list again while the title is in generation, until the title is there', async () => {
    const session = await openSession();
    titleState = 'generating';
    fakeSocket().receive({ type: 'run_state', state: 'settled' });

    await vi.advanceTimersByTimeAsync(3 * READ_DELAY_MILLISECONDS);
    expect(session.conversation?.title).toBe('New conversation');
    titleState = 'generated';
    title = 'Moving averages';
    await vi.advanceTimersByTimeAsync(5 * READ_DELAY_MILLISECONDS);

    expect(session.conversation?.title).toBe('Moving averages');
    expect(listReadCount).toBe(4);
  });

  it('stops at the read limit', async () => {
    await openSession();
    titleState = 'generating';
    fakeSocket().receive({ type: 'run_state', state: 'settled' });

    await vi.advanceTimersByTimeAsync(2 * READ_LIMIT * READ_DELAY_MILLISECONDS);

    expect(listReadCount).toBe(READ_LIMIT);
  });

  it('stops when the socket closes', async () => {
    await openSession();
    titleState = 'generating';
    fakeSocket().receive({ type: 'run_state', state: 'settled' });
    await vi.advanceTimersByTimeAsync(READ_DELAY_MILLISECONDS);

    fakeSocket().close();
    await vi.advanceTimersByTimeAsync(5 * READ_DELAY_MILLISECONDS);

    expect(listReadCount).toBeLessThanOrEqual(2);
  });
});

describe('a title read in flight', () => {
  it('keeps the conversation that the user opens during the read', async () => {
    const session = await openSession();
    const answers: ((response: Response) => void)[] = [];
    vi.stubGlobal('fetch', (input: RequestInfo | URL) =>
      (input as string).endsWith('/conversations')
        ? new Promise<Response>((resolve) => {
            answers.push(resolve);
          })
        : fakeFetch(input),
    );
    fakeSocket().receive({ type: 'run_state', state: 'settled' });
    await vi.advanceTimersByTimeAsync(READ_DELAY_MILLISECONDS);

    session.openConversation(OTHER_CONVERSATION_ID);
    const otherSocket = fakeSocket();
    const conversations = [CONVERSATION_ID, OTHER_CONVERSATION_ID].map((id) => ({
      id,
      title,
      title_state: titleState,
      created_at_utc: '2026-01-02T03:04:05Z',
    }));
    answers[0]?.(jsonResponse({ conversations }));
    await vi.advanceTimersByTimeAsync(0);

    expect(session.conversationId).toBe(OTHER_CONVERSATION_ID);
    expect(fakeSocket()).toBe(otherSocket);
    expect(session.conversations).toHaveLength(2);
  });
});

describe('send', () => {
  const SELECTION = { provider: 'fake', model: 'fake-model', credentialId: 'key-1' };

  it('sends the input and clears it', async () => {
    const session = await openSession();
    session.selection = SELECTION;
    session.text = 'Hello';

    expect(session.send()).toBe(true);

    expect(session.text).toBe('');
    expect(session.log.items).toHaveLength(1);
    expect(fakeSocket().sent).toHaveLength(1);
  });

  it('keeps the input during a run: web refuses the prompt', async () => {
    const session = await openSession();
    session.selection = SELECTION;
    fakeSocket().receive({ type: 'run_state', state: 'running' });
    session.text = 'Hello';

    expect(session.send()).toBe(false);

    expect(session.text).toBe('Hello');
    expect(session.log.items).toHaveLength(0);
    expect(fakeSocket().sent).toHaveLength(0);
  });

  it('keeps the input without a credential: web refuses the prompt', async () => {
    const session = await openSession();
    session.selection = { ...SELECTION, credentialId: '' };
    session.text = 'Hello';

    expect(session.send()).toBe(false);

    expect(session.text).toBe('Hello');
    expect(session.log.items).toHaveLength(0);
    expect(fakeSocket().sent).toHaveLength(0);
  });
});
