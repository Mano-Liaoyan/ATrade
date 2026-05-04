export type AssetClass = 'Stock' | 'ETF';

export type ChartRange = '1min' | '5mins' | '1h' | '6h' | '1D' | '1m' | '6m' | '1y' | '5y' | 'all';

export type Timeframe = ChartRange;

export const SUPPORTED_CHART_RANGES: ChartRange[] = ['1min', '5mins', '1h', '6h', '1D', '1m', '6m', '1y', '5y', 'all'];

export const SUPPORTED_TIMEFRAMES = SUPPORTED_CHART_RANGES;

export const CHART_RANGE_LABELS: Record<ChartRange, string> = {
  '1min': '1min',
  '5mins': '5mins',
  '1h': '1h',
  '6h': '6h',
  '1D': '1D',
  '1m': '1m',
  '6m': '6m',
  '1y': '1y',
  '5y': '5y',
  all: 'All time',
};

export const CHART_RANGE_DESCRIPTIONS: Record<ChartRange, string> = {
  '1min': 'Past 1 minute from now',
  '5mins': 'Past 5 minutes from now',
  '1h': 'Past 1 hour from now',
  '6h': 'Past 6 hours from now',
  '1D': 'Past day from now',
  '1m': 'Past month from now',
  '6m': 'Past six months from now',
  '1y': 'Past year from now',
  '5y': 'Past five years from now',
  all: 'All available history',
};

export type MarketDataSymbol = {
  symbol: string;
  name: string;
  assetClass: AssetClass | string;
  exchange: string;
  sector: string;
  lastPrice: number;
  changePercent: number;
  averageVolume?: number;
  identity?: MarketDataSymbolIdentity | null;
};

export type TrendingFactorBreakdown = {
  volumeSpike: number;
  priceMomentum: number;
  volatility: number;
  externalSignal: number;
};

export type TrendingSymbol = MarketDataSymbol & {
  score: number;
  factors: TrendingFactorBreakdown;
  reasons: string[];
};

export type TrendingSymbolsResponse = {
  generatedAt: string;
  symbols: TrendingSymbol[];
  source: string;
};

export type MarketDataSymbolIdentity = {
  symbol: string;
  provider: string;
  providerSymbolId: string | null;
  assetClass: string;
  exchange: string;
  currency: string;
};

export type MarketDataSymbolSearchResult = {
  identity: MarketDataSymbolIdentity;
  name: string;
  sector: string;
  symbol: string;
  provider: string;
  providerSymbolId: string | null;
  assetClass: string;
  exchange: string;
  currency: string;
};

export type MarketDataSymbolSearchResponse = {
  generatedAt: string;
  results: MarketDataSymbolSearchResult[];
  source: string;
};

export type OhlcvCandle = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type CandleSeriesResponse = {
  symbol: string;
  timeframe: Timeframe;
  generatedAt: string;
  candles: OhlcvCandle[];
  source: string;
  identity?: MarketDataSymbolIdentity | null;
};

export type MovingAveragePoint = {
  time: string;
  sma20: number;
  sma50: number;
};

export type RsiPoint = {
  time: string;
  value: number;
};

export type MacdPoint = {
  time: string;
  macd: number;
  signal: number;
  histogram: number;
};

export type IndicatorResponse = {
  symbol: string;
  timeframe: Timeframe;
  movingAverages: MovingAveragePoint[];
  rsi: RsiPoint[];
  macd: MacdPoint[];
  source: string;
  identity?: MarketDataSymbolIdentity | null;
};

export type MarketDataUpdate = {
  symbol: string;
  timeframe: Timeframe;
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  changePercent: number;
  source: string;
  identity?: MarketDataSymbolIdentity | null;
};
