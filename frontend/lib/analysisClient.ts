import { buildApiUrl } from './apiBaseUrl';
import type { AnalysisEngineDescriptor, AnalysisError, AnalysisResult, RunAnalysisRequest } from '../types/analysis';

export class AnalysisClientError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
    readonly result?: AnalysisResult,
  ) {
    super(message);
    this.name = 'AnalysisClientError';
  }
}

export async function getAnalysisEngines(): Promise<AnalysisEngineDescriptor[]> {
  return fetchJson<AnalysisEngineDescriptor[]>('/api/analysis/engines');
}

export async function runAnalysis(request: RunAnalysisRequest): Promise<AnalysisResult> {
  return fetchJson<AnalysisResult>('/api/analysis/run', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
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

  if (!response.ok) {
    const body = await response.text();
    const parsed = parseJson(body);
    const analysisResult = isAnalysisResult(parsed) ? parsed : undefined;
    const error = readError(parsed, analysisResult);
    throw new AnalysisClientError(formatAnalysisError(response.status, error), response.status, error?.code, analysisResult);
  }

  return response.json() as Promise<T>;
}

function parseJson(body: string): unknown {
  try {
    return JSON.parse(body) as unknown;
  } catch {
    return null;
  }
}

function isAnalysisResult(value: unknown): value is AnalysisResult {
  return Boolean(value && typeof value === 'object' && 'status' in value && 'engine' in value && 'source' in value);
}

function readError(parsed: unknown, analysisResult: AnalysisResult | undefined): AnalysisError | undefined {
  if (analysisResult?.error) {
    return analysisResult.error;
  }

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

  return code || message ? { code: code ?? 'analysis-request-failed', message: message ?? 'Analysis request failed.' } : undefined;
}

function formatAnalysisError(status: number, error: AnalysisError | undefined): string {
  if (error?.code === 'analysis-engine-not-configured') {
    return error.message || 'No analysis engine is configured.';
  }

  if (error?.code === 'analysis-engine-unavailable') {
    return error.message || 'The configured analysis engine is unavailable.';
  }

  if (error?.code === 'analysis-request-invalid') {
    return error.message || 'The analysis request is invalid.';
  }

  return error?.message ?? `ATrade analysis request failed with HTTP ${status}.`;
}
