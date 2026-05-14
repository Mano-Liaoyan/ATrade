'use client';

import * as signalR from '@microsoft/signalr';

import { buildApiUrl } from './apiBaseUrl';

export type WorkspaceSignalRState = 'connecting' | 'connected' | 'reconnecting' | 'closed' | 'unavailable';
export type WorkspaceHttpReadState = 'unchecked' | 'checking' | 'healthy' | 'degraded' | 'unavailable';
export type WorkspaceCacheReadState = 'ready' | 'degraded' | 'unavailable';
export type WorkspaceStatusId = 'connected' | 'connecting' | 'fallback' | 'disconnected' | 'cache-read-degraded' | 'unavailable';

export type WorkspaceStatusState = {
  signalRState: WorkspaceSignalRState;
  httpReadState: WorkspaceHttpReadState;
  cacheReadState: WorkspaceCacheReadState;
};

export type WorkspaceStatusProjection = {
  id: WorkspaceStatusId;
  label: string;
  detail: string;
  pulse: boolean;
  tone: 'neutral' | 'info' | 'success' | 'warning' | 'danger';
};

export type WorkspaceStatusStreamSubscription = {
  connection: signalR.HubConnection;
  stop: () => Promise<void>;
};

export type ConnectWorkspaceStatusStreamOptions = {
  onStateChange?: (state: WorkspaceSignalRState) => void;
};

const WORKSPACE_STATUS_HEALTH_PATH = '/health';
const WORKSPACE_STATUS_STREAM_PATH = '/hubs/backtests';
const WATCHLIST_CACHE_KEY = 'atrade.paperTrading.watchlist.v1';

export function createInitialWorkspaceStatusState(): WorkspaceStatusState {
  return {
    signalRState: 'connecting',
    httpReadState: 'unchecked',
    cacheReadState: readLocalWorkspaceCacheState(),
  };
}

export function projectWorkspaceSignalRStatus(state: WorkspaceStatusState): WorkspaceStatusProjection {
  if (state.cacheReadState === 'degraded' || state.httpReadState === 'degraded') {
    return {
      id: 'cache-read-degraded',
      label: 'cache/read degraded',
      detail: 'Cache/read degraded; cached views may be stale until ATrade.Api reads recover.',
      pulse: false,
      tone: 'warning',
    };
  }

  if (state.signalRState === 'connected') {
    return {
      id: 'connected',
      label: 'connected',
      detail: 'Live workspace updates are connected; HTTP reads remain authoritative.',
      pulse: false,
      tone: 'success',
    };
  }

  if (state.signalRState === 'connecting' || state.signalRState === 'reconnecting') {
    return {
      id: 'connecting',
      label: state.signalRState === 'reconnecting' ? 'reconnecting' : 'connecting',
      detail: 'Initial status is local; ATrade.Api checks refine this indicator after first render.',
      pulse: true,
      tone: 'info',
    };
  }

  if ((state.signalRState === 'closed' && state.httpReadState === 'healthy') || (state.signalRState === 'unavailable' && state.httpReadState === 'healthy')) {
    return {
      id: 'fallback',
      label: 'fallback',
      detail: 'HTTP read fallback active; no synthetic stream data is shown.',
      pulse: false,
      tone: 'warning',
    };
  }

  if (state.signalRState === 'closed' && state.httpReadState !== 'unavailable') {
    return {
      id: 'disconnected',
      label: 'disconnected',
      detail: 'Stream disconnected while the HTTP read path is still being checked.',
      pulse: false,
      tone: 'neutral',
    };
  }

  return {
    id: 'unavailable',
    label: 'unavailable',
    detail: 'Workspace status is unavailable; retry after ATrade.Api becomes reachable.',
    pulse: false,
    tone: 'danger',
  };
}

export async function connectWorkspaceStatusStream(options: ConnectWorkspaceStatusStreamOptions): Promise<WorkspaceStatusStreamSubscription> {
  if (typeof window === 'undefined') {
    throw new Error('Workspace streaming status is only available in the browser.');
  }

  options.onStateChange?.('connecting');

  const connection = new signalR.HubConnectionBuilder()
    .withUrl(buildApiUrl(WORKSPACE_STATUS_STREAM_PATH))
    .withAutomaticReconnect()
    .configureLogging(signalR.LogLevel.Warning)
    .build();

  connection.onreconnecting(() => options.onStateChange?.('reconnecting'));
  connection.onreconnected(() => options.onStateChange?.('connected'));
  connection.onclose(() => options.onStateChange?.('closed'));

  await connection.start();
  options.onStateChange?.('connected');

  return {
    connection,
    stop: () => connection.stop(),
  };
}

export async function checkWorkspaceHttpReadState(): Promise<WorkspaceHttpReadState> {
  try {
    const response = await fetch(buildApiUrl(WORKSPACE_STATUS_HEALTH_PATH), {
      cache: 'no-store',
      headers: {
        Accept: 'text/plain',
      },
    });

    return response.ok ? 'healthy' : 'degraded';
  } catch {
    return 'unavailable';
  }
}

export function readLocalWorkspaceCacheState(): WorkspaceCacheReadState {
  if (typeof window === 'undefined') {
    return 'ready';
  }

  try {
    window.localStorage.getItem(WATCHLIST_CACHE_KEY);
    return 'ready';
  } catch {
    return 'degraded';
  }
}
