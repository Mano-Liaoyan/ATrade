import * as signalR from '@microsoft/signalr';

import { buildApiUrl } from './apiBaseUrl';
import type {
  BacktestCreateRequest,
  BacktestError,
  BacktestRunEnvelope,
  BacktestRunUpdatePayload,
  LocalPaperCapitalUpdateRequest,
  PaperCapitalResponse,
} from '../types/backtesting';
import { BACKTEST_RUN_UPDATE_EVENTS } from '../types/backtesting';

export type BacktestStreamState = 'connecting' | 'connected' | 'reconnecting' | 'closed' | 'unavailable';

export type BacktestStreamSubscription = {
  connection: signalR.HubConnection;
  stop: () => Promise<void>;
};

export type ConnectBacktestRunStreamOptions = {
  onUpdate: (update: BacktestRunUpdatePayload) => void;
  onStateChange?: (state: BacktestStreamState) => void;
};

export class BacktestClientError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
    readonly payload?: unknown,
  ) {
    super(message);
    this.name = 'BacktestClientError';
  }
}

export async function getPaperCapital(): Promise<PaperCapitalResponse> {
  return fetchJson<PaperCapitalResponse>('/api/accounts/paper-capital');
}

export async function updateLocalPaperCapital(request: LocalPaperCapitalUpdateRequest): Promise<PaperCapitalResponse> {
  return fetchJson<PaperCapitalResponse>('/api/accounts/local-paper-capital', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

export async function createBacktestRun(request: BacktestCreateRequest): Promise<BacktestRunEnvelope> {
  return fetchJson<BacktestRunEnvelope>('/api/backtests', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

export async function listBacktestRuns(limit = 50): Promise<BacktestRunEnvelope[]> {
  const params = new URLSearchParams();
  if (Number.isFinite(limit) && limit > 0) {
    params.set('limit', String(Math.trunc(limit)));
  }

  const query = params.toString();
  return fetchJson<BacktestRunEnvelope[]>(`/api/backtests${query ? `?${query}` : ''}`);
}

export async function getBacktestRun(id: string): Promise<BacktestRunEnvelope> {
  return fetchJson<BacktestRunEnvelope>(`/api/backtests/${encodeURIComponent(id)}`);
}

export async function cancelBacktestRun(id: string): Promise<BacktestRunEnvelope> {
  return fetchJson<BacktestRunEnvelope>(`/api/backtests/${encodeURIComponent(id)}/cancel`, {
    method: 'POST',
  });
}

export async function retryBacktestRun(id: string): Promise<BacktestRunEnvelope> {
  return fetchJson<BacktestRunEnvelope>(`/api/backtests/${encodeURIComponent(id)}/retry`, {
    method: 'POST',
  });
}

export async function connectBacktestRunStream(options: ConnectBacktestRunStreamOptions): Promise<BacktestStreamSubscription> {
  if (typeof window === 'undefined') {
    throw new Error('Backtest status streaming is only available in the browser.');
  }

  options.onStateChange?.('connecting');

  const connection = new signalR.HubConnectionBuilder()
    .withUrl(buildApiUrl('/hubs/backtests'))
    .withAutomaticReconnect()
    .configureLogging(signalR.LogLevel.Warning)
    .build();

  for (const eventName of BACKTEST_RUN_UPDATE_EVENTS) {
    connection.on(eventName, options.onUpdate);
  }

  connection.onreconnecting(() => options.onStateChange?.('reconnecting'));
  connection.onreconnected(() => options.onStateChange?.('connected'));
  connection.onclose(() => options.onStateChange?.('closed'));

  await connection.start();
  options.onStateChange?.('connected');

  return {
    connection,
    stop: async () => {
      for (const eventName of BACKTEST_RUN_UPDATE_EVENTS) {
        connection.off(eventName, options.onUpdate);
      }

      await connection.stop();
    },
  };
}

async function fetchJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(buildApiUrl(path), {
    cache: 'no-store',
    headers: {
      Accept: 'application/json',
      ...init.headers,
    },
    ...init,
  });

  const body = await response.text();
  const parsed = parseJson(body);

  if (!response.ok) {
    const error = readBacktestError(parsed);
    throw new BacktestClientError(formatBacktestError(response.status, error), response.status, error?.code, parsed);
  }

  if (parsed === null) {
    throw new BacktestClientError(`ATrade.Api returned an empty response for ${path}.`, response.status);
  }

  return parsed as T;
}

function parseJson(body: string): unknown {
  if (!body.trim()) {
    return null;
  }

  try {
    return JSON.parse(body) as unknown;
  } catch {
    return null;
  }
}

function readBacktestError(parsed: unknown): BacktestError | undefined {
  if (!parsed || typeof parsed !== 'object') {
    return undefined;
  }

  const maybeError = parsed as { code?: unknown; message?: unknown; error?: unknown };
  const code = typeof maybeError.code === 'string' ? maybeError.code : undefined;
  const message = typeof maybeError.message === 'string'
    ? maybeError.message
    : typeof maybeError.error === 'string'
      ? maybeError.error
      : undefined;

  return code || message ? { code: code ?? 'backtest-request-failed', message: message ?? 'Backtest request failed.' } : undefined;
}

function formatBacktestError(status: number, error: BacktestError | undefined): string {
  if (error?.code === 'backtest-capital-unavailable') {
    return error.message || 'No effective paper capital source is configured for backtest creation.';
  }

  if (error?.code === 'backtest-analysis-unavailable') {
    return error.message || 'Analysis engine is unavailable for backtest execution.';
  }

  if (error?.code === 'backtest-market-data-unavailable') {
    return error.message || 'Market data is unavailable for backtest execution.';
  }

  if (error?.code === 'backtest-storage-unavailable') {
    return error.message || 'Backtest storage is unavailable.';
  }

  if (error?.code === 'paper-capital-source-unavailable') {
    return error.message || 'Paper capital is unavailable.';
  }

  return error?.message ?? `ATrade backtest request failed with HTTP ${status}.`;
}
