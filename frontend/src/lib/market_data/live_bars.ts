// Live bars of /ws/market-data: the socket path of a chart, the messages, and which live bars the chart can draw.
// The message types come from the JSON Schema of the backend message models (docs/architecture.md section 13).
import type { components } from '#lib/api';
import { readSocketMessage } from '#lib/foundation/live_socket';
import type { Bar, ChartRequest } from './bars';

export type LiveBarMessage = components['schemas']['LiveBarMessage'];
export type LiveBarErrorMessage = components['schemas']['LiveBarErrorMessage'];

const LIVE_BARS_SOCKET_PATH = '/ws/market-data';

export function formatLiveBarsPath(chartRequest: ChartRequest): string {
  const { symbol, exchange, currency } = chartRequest.instrument;
  const searchParameters = new URLSearchParams({ symbol, exchange, currency, bar_period: chartRequest.barPeriod });
  return `${LIVE_BARS_SOCKET_PATH}?${searchParameters.toString()}`;
}

/** Returns the bar or error message. The frontend trusts the backend types and checks only the message type. */
export function readLiveBarMessage(message: unknown): LiveBarMessage | LiveBarErrorMessage | null {
  return readSocketMessage<LiveBarMessage | LiveBarErrorMessage>(message, ['bar', 'error']);
}

/** The chart can replace its last bar or add a later bar. It cannot change an older bar. */
export function canDrawLiveBar(bars: readonly Bar[], liveBar: Bar): boolean {
  const lastBar = bars.at(-1);
  return lastBar === undefined || liveBar.time >= lastBar.time;
}

const MILLISECONDS_PER_SECOND = 1000;
// "2026-01-02T03:00" is the first 16 characters of the ISO text.
const ISO_MINUTE_LENGTH = 16;
const CLOSE_FORMAT = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 4,
  useGrouping: false,
});

export function describeLiveBar(bar: Bar): string {
  // ISO text is UTC: "2026-01-02T03:00:00.000Z" becomes "2026-01-02 03:00".
  const startText = new Date(bar.time * MILLISECONDS_PER_SECOND).toISOString().slice(0, ISO_MINUTE_LENGTH).replace('T', ' ');
  return `Live bar ${startText} UTC: close ${CLOSE_FORMAT.format(bar.close)}`;
}
