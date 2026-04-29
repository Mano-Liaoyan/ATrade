export type AssetClass = 'Stock' | 'ETF';

export type Timeframe = '1m' | '5m' | '1h' | '1D';

export const SUPPORTED_TIMEFRAMES: Timeframe[] = ['1m', '5m', '1h', '1D'];

export type MarketDataSymbol = {
  symbol: string;
  name: string;
  assetClass: AssetClass;
  exchange: string;
  sector: string;
  lastPrice: number;
  changePercent: number;
  averageVolume?: number;
};

export type TrendingFactorBreakdown = {
  volumeSpike: number;
  priceMomentum: number;
  volatility: number;
  newsSentimentPlaceholder: number;
};

export type TrendingSymbol = MarketDataSymbol & {
  score: number;
  factors: TrendingFactorBreakdown;
  reasons: string[];
};

export type TrendingSymbolsResponse = {
  generatedAt: string;
  symbols: TrendingSymbol[];
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
};
