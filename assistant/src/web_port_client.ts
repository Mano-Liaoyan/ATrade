// The HTTP client of the tools: each tool calls only the routes of port 8001 of web (docs/architecture/assistant.md
// 25.3.2, 25.3.3). Each request sends the conversation ID in the header X-ATrade-Conversation-Id.

// The service name of web in deploy/compose.yaml and ASSISTANT_PORT of backend/src/atrade/app/assistant_port.py.
export const WEB_PORT_URL = 'http://web:8001';
export const CONVERSATION_HEADER = 'X-ATrade-Conversation-Id';

export interface WebPortAnswer {
  status: number;
  /** The JSON body, or the text of a body that is not JSON. */
  body: unknown;
}

export class WebPortClient {
  private readonly baseUrl: string;
  private readonly conversationId: string;

  constructor(baseUrl: string, conversationId: string) {
    this.baseUrl = baseUrl;
    this.conversationId = conversationId;
  }

  async request(method: 'GET' | 'POST', path: string, body?: unknown, signal?: AbortSignal): Promise<WebPortAnswer> {
    const headers: Record<string, string> = { [CONVERSATION_HEADER]: this.conversationId };
    if (body !== undefined) {
      headers['content-type'] = 'application/json';
    }
    const response = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
    const text = await response.text();
    try {
      return { status: response.status, body: JSON.parse(text) as unknown };
    } catch {
      return { status: response.status, body: text };
    }
  }
}
