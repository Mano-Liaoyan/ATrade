import * as signalR from '@microsoft/signalr';
import { buildApiUrl } from './apiBaseUrl';
import type { ChartRange, MarketDataUpdate } from '../types/marketData';

export type MarketDataStreamState = 'connecting' | 'connected' | 'reconnecting' | 'closed' | 'unavailable';

export type MarketDataStreamSubscription = {
  connection: signalR.HubConnection;
  stop: () => Promise<void>;
};

export type ConnectMarketDataStreamOptions = {
  symbol: string;
  chartRange: ChartRange;
  onUpdate: (update: MarketDataUpdate) => void;
  onStateChange?: (state: MarketDataStreamState) => void;
};

export async function connectMarketDataStream(options: ConnectMarketDataStreamOptions): Promise<MarketDataStreamSubscription> {
  if (typeof window === 'undefined') {
    throw new Error('Market-data streaming is only available in the browser.');
  }

  options.onStateChange?.('connecting');

  const connection = new signalR.HubConnectionBuilder()
    .withUrl(buildApiUrl('/hubs/market-data'))
    .withAutomaticReconnect()
    .configureLogging(signalR.LogLevel.Warning)
    .build();

  connection.on('marketDataUpdated', options.onUpdate);
  connection.onreconnecting(() => options.onStateChange?.('reconnecting'));
  connection.onreconnected(() => options.onStateChange?.('connected'));
  connection.onclose(() => options.onStateChange?.('closed'));

  await connection.start();
  await connection.invoke('Subscribe', options.symbol.toUpperCase(), options.chartRange);
  options.onStateChange?.('connected');

  return {
    connection,
    stop: async () => {
      try {
        await connection.invoke('Unsubscribe', options.symbol.toUpperCase(), options.chartRange);
      } finally {
        await connection.stop();
      }
    },
  };
}
