// Type definitions for AI Trader

export type SignalType = 'BUY' | 'SELL' | 'HOLD';
export type TrendType = 'bullish' | 'bearish' | 'neutral';
export type PatternType = 'Hammer' | 'Shooting Star' | 'Bullish Engulfing' | 'Bearish Engulfing' | 'Doji' | 'Morning Star' | 'Evening Star' | 'None';

export interface StockInfo {
  symbol: string;
  name: string;
  exchange: string;
  current_price: number;
  previous_close: number;
  change: number;
  change_percent: number;
  open: number;
  high: number;
  low: number;
  volume: number;
  timestamp: string;
}

export interface TechnicalIndicators {
  sma_20?: number;
  sma_50?: number;
  sma_200?: number;
  rsi?: number;
  macd?: number;
  macd_signal?: number;
  macd_histogram?: number;
  support?: number;
  resistance?: number;
  avg_volume?: number;
  volume_ratio?: number;
  price_vs_sma20?: number;
  price_vs_sma50?: number;
}

export interface TradingSignal {
  stock: StockInfo;
  indicators: TechnicalIndicators;
  signal: SignalType;
  confidence: number;
  trend: TrendType;
  pattern: PatternType;
  entry_price?: number;
  target_price?: number;
  stop_loss?: number;
  risk_reward?: number;
  explanation: string;
  generated_at: string;
  signal_strength: 'WEAK' | 'MEDIUM' | 'STRONG';
}

export interface SignalsResponse {
  timestamp: string;
  count: number;
  buy_count: number;
  sell_count: number;
  hold_count: number;
  signals: TradingSignal[];
}

export interface IndexData {
  index_name: string;
  current_value: number;
  change: number;
  change_percent: number;
  timestamp: string;
}

export interface HealthCheck {
  status: string;
  service: string;
  timestamp: string;
  ai_enabled: boolean;
  data_source: string;
  indices_loaded: boolean;
}
