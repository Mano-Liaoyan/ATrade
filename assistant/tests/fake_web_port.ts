// A local fake of port 8001 of web (docs/architecture/assistant.md 25.3.3). It keeps each request with its
// conversation header. Each GET of a backtest moves the backtest to the next status of `backtestStatuses`.
import { createServer, type IncomingMessage, type Server } from 'node:http';
import type { AddressInfo } from 'node:net';

export interface WebPortRequest {
  method: string;
  path: string;
  conversationId: string | undefined;
  body: unknown;
}

export interface FakeAnswer {
  status: number;
  body: unknown;
}

export interface FakeWebPort {
  baseUrl: string;
  requests: WebPortRequest[];
  /** The answers of the strategy version saves, in order. After the last: 201 with a new version. */
  saveAnswers: FakeAnswer[];
  /** The status of a backtest at its start, then after each GET. The last status stays. */
  backtestStatuses: string[];
  /** POST /api/backtests answers 422: no saved bars. */
  hasNoSavedBars: boolean;
  /** The answers of the screen creates, changes, and runs, in order. After the last: the success answer. */
  screenAnswers: FakeAnswer[];
  close: () => Promise<void>;
}

export const STRATEGY_LIST = [{ id: 3, name: 'SMA crossover', latest_version_number: 2 }];
export const STRATEGY = { id: 3, name: 'SMA crossover', created_at_utc: '2026-01-02T03:04:05Z', versions: [] };
export const COMPARISON = { strategy_id: 3, strategy_name: 'SMA crossover', first: { id: 11 }, second: { id: 12 } };
export const NO_SAVED_BARS = { detail: 'No saved bars for AAPL NASDAQ USD 1-DAY in the range.' };
export const EQUITY_POINT_COUNT = 120;
export const SCREEN_DEFINITION = { start: 'quarter_universe', filters: [], indicator_conditions: [] };
export const SCREEN = {
  id: 5,
  name: 'Momentum leaders (AI)',
  market: 'US',
  definition: SCREEN_DEFINITION,
  kept: false,
  assistant_conversation_id: 7,
};
/** The screen of the user that create_screen names as its source screen. */
export const SOURCE_SCREEN = { ...SCREEN, id: 4, name: 'Momentum leaders', definition: { start: 'watchlist' }, kept: true };
export const SCREEN_LIST = [{ id: 5, name: 'Momentum leaders (AI)', market: 'US', kept: false }];
export const SCREEN_ROW_COUNT = 120;
export const SCREEN_SUMMARY = {
  row_count: SCREEN_ROW_COUNT,
  start_count: 500,
  after_filters_count: 300,
  after_indicator_conditions_count: SCREEN_ROW_COUNT,
  result_count: SCREEN_ROW_COUNT,
  exclusion_counts: [{ reason: 'Filter 2: last_price > 5', count: 200 }],
  daily_bars_date: '2025-12-31',
  run_at_utc: '2026-01-02T03:04:05Z',
  run_seconds: 1.5,
};

export function screenRow(position: number) {
  return { position, symbol: `S${String(position)}`, exchange: 'NASDAQ', currency: 'USD', last_price: '10' };
}

/** GET /api/screen-results/9 as port 8001 gives it: one page of rows and all exclusions. */
export function screenResultBody(offset: number, limit: number) {
  const last = Math.min(offset + limit, SCREEN_ROW_COUNT);
  return {
    id: 9,
    screen_id: 5,
    market: 'US',
    assistant_conversation_id: 7,
    summary: SCREEN_SUMMARY,
    definition: { start: 'quarter_universe' },
    rows: Array.from({ length: Math.max(last - offset, 0) }, (_unused, index) => screenRow(offset + index + 1)),
    exclusions: [{ symbol: 'X', exchange: 'NYSE', currency: 'USD', reason: 'Filter 2: last_price > 5' }],
  };
}
export const TRADE_COUNT = 60;

export function versionBody(versionNumber: number) {
  const isRuleBuilder = versionNumber === 1;
  return {
    id: 100 + versionNumber,
    strategy_id: 3,
    version_number: versionNumber,
    code: `# code of version ${String(versionNumber)}\n`,
    code_sha256: 'sha',
    created_at_utc: '2026-01-02T03:04:05Z',
    source: isRuleBuilder ? 'rule_builder' : 'user',
    rules: isRuleBuilder ? { entry: [{ indicator: 'SMA' }] } : null,
    conversation_id: null,
    discarded: false,
  };
}

export function backtestBody(id: number, status: string) {
  return {
    id,
    strategy_version_id: 102,
    status,
    metrics: status === 'finished' ? { final_equity_usd: '10500', trade_count: TRADE_COUNT } : null,
    conversation_id: 7,
    equity_curve: Array.from({ length: EQUITY_POINT_COUNT }, (_unused, index) => ({
      time_utc: `point ${String(index)}`,
      equity_usd: String(10_000 + index),
    })),
    trades: Array.from({ length: TRADE_COUNT }, (_unused, index) => ({
      time_utc: `trade ${String(index)}`,
      side: index % 2 === 0 ? 'BUY' : 'SELL',
      quantity_shares: '1',
      price_usd: '100',
      commission_usd: '1',
    })),
  };
}

async function readBody(request: IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = [];
  for await (const chunk of request) {
    chunks.push(chunk as Buffer);
  }
  const text = Buffer.concat(chunks).toString('utf8');
  return text === '' ? undefined : (JSON.parse(text) as unknown);
}

class FakeRoutes {
  readonly port: Omit<FakeWebPort, 'baseUrl' | 'close'>;
  private readonly backtestSteps = new Map<number, number>();
  private nextBacktestId = 11;
  private nextVersionNumber = 3;

  constructor(port: Omit<FakeWebPort, 'baseUrl' | 'close'>) {
    this.port = port;
  }

  answer(method: string, path: string): FakeAnswer {
    const route = `${method} ${path}`;
    const versionMatch = /^GET \/api\/strategies\/3\/versions\/(\d+)$/u.exec(route);
    if (versionMatch !== null) {
      return { status: 200, body: versionBody(Number(versionMatch[1])) };
    }
    const resultMatch = /^GET \/api\/screen-results\/9\?offset=(\d+)&limit=(\d+)$/u.exec(route);
    if (resultMatch !== null) {
      return { status: 200, body: screenResultBody(Number(resultMatch[1]), Number(resultMatch[2])) };
    }
    const backtestMatch = /^GET \/api\/backtests\/(\d+)$/u.exec(route);
    if (backtestMatch !== null) {
      return this.readBacktest(Number(backtestMatch[1]));
    }
    const fixed: Record<string, () => FakeAnswer> = {
      'GET /api/strategies': () => ({ status: 200, body: STRATEGY_LIST }),
      'GET /api/strategies/3': () => ({ status: 200, body: STRATEGY }),
      'POST /api/strategies': () => ({ status: 201, body: { ...STRATEGY, id: 4 } }),
      'POST /api/strategies/3/versions': () => this.save(),
      'POST /api/backtests': () => this.startBacktest(),
      'GET /api/backtests': () => ({ status: 200, body: [backtestBody(11, 'finished')] }),
      'GET /api/backtests/11/comparison/12': () => ({ status: 200, body: COMPARISON }),
      'GET /api/screens': () => ({ status: 200, body: SCREEN_LIST }),
      'GET /api/screens/5': () => ({ status: 200, body: SCREEN }),
      'GET /api/screens/4': () => ({ status: 200, body: SOURCE_SCREEN }),
      'POST /api/screens': () => this.screenAnswer({ status: 201, body: SCREEN }),
      'PUT /api/screens/5': () => this.screenAnswer({ status: 200, body: SCREEN }),
      'POST /api/screens/5/runs': () => this.screenAnswer({ status: 201, body: screenResultBody(0, 50) }),
    };
    return fixed[route]?.() ?? { status: 404, body: { detail: 'Not Found' } };
  }

  private screenAnswer(success: FakeAnswer): FakeAnswer {
    return this.port.screenAnswers.shift() ?? success;
  }

  private save(): FakeAnswer {
    const answer = this.port.saveAnswers.shift();
    if (answer !== undefined) {
      return answer;
    }
    const version = versionBody(this.nextVersionNumber);
    this.nextVersionNumber += 1;
    return { status: 201, body: { ...version, source: 'ai_assistant', conversation_id: 7 } };
  }

  private startBacktest(): FakeAnswer {
    if (this.port.hasNoSavedBars) {
      return { status: 422, body: NO_SAVED_BARS };
    }
    const id = this.nextBacktestId;
    this.nextBacktestId += 1;
    this.backtestSteps.set(id, 0);
    return { status: 201, body: backtestBody(id, this.port.backtestStatuses[0] ?? 'queued') };
  }

  private readBacktest(id: number): FakeAnswer {
    const step = Math.min((this.backtestSteps.get(id) ?? 0) + 1, this.port.backtestStatuses.length - 1);
    this.backtestSteps.set(id, step);
    return { status: 200, body: backtestBody(id, this.port.backtestStatuses[step] ?? 'finished') };
  }
}

export async function startFakeWebPort(): Promise<FakeWebPort> {
  const state = {
    requests: [] as WebPortRequest[],
    saveAnswers: [] as FakeAnswer[],
    backtestStatuses: ['queued', 'running', 'finished'],
    hasNoSavedBars: false,
    screenAnswers: [] as FakeAnswer[],
  };
  const routes = new FakeRoutes(state);
  const server: Server = createServer((request, response) => {
    void readBody(request).then((body) => {
      const method = request.method ?? '';
      const path = request.url ?? '';
      const header = request.headers['x-atrade-conversation-id'];
      state.requests.push({ method, path, conversationId: typeof header === 'string' ? header : undefined, body });
      const answer = routes.answer(method, path);
      response.writeHead(answer.status, { 'content-type': 'application/json' });
      response.end(JSON.stringify(answer.body));
    });
  });
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  const { port } = server.address() as AddressInfo;
  return Object.assign(state, {
    baseUrl: `http://127.0.0.1:${String(port)}`,
    close: () =>
      new Promise<void>((resolve) => {
        server.closeAllConnections();
        server.close(() => {
          resolve();
        });
      }),
  });
}
