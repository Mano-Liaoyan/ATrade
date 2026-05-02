export type AssetClass = 'Stock' | 'ETF';

export type Timeframe = '1m' | '5m' | '1h' | '1D';

export const SUPPORTED_TIMEFRAMES: Timeframe[] = ['1m', '5m', '1h', '1D'];

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
