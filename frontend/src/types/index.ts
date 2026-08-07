// Type definitions for AI Trader v2.0

export type SignalType = 'BUY' | 'SELL' | 'HOLD';
export type TrendType = 'bullish' | 'bearish' | 'neutral';

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
  rsi?: number;
  sma_20?: number;
  sma_50?: number;
  sma_200?: number;
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
  pattern: string;
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

export interface ArthAnalysis {
  symbol: string;
  company_name: string;
  timestamp: string;
  price: {
    current: number;
    change: number;
    change_percent: number;
    open: number;
    high: number;
    low: number;
    volume: number;
  };
  indicators: TechnicalIndicators;
  signal: SignalType;
  confidence: number;
  source: string;
  ai_enhanced: boolean;
  ai_provider?: string;
  ai_reasoning?: string;
  probability: {
    symbol: string;
    signal: string;
    win_probability: number;
    position_size: string;
    risk_level: string;
    confidence_components: Record<string, number>;
  };
  levels: {
    entry?: number;
    target?: number;
    stop_loss?: number;
    risk_reward?: number;
  };
  patterns: Array<{ name: string; type: string; reliability: number }>;
  key_factors: string[];
  risks: string[];
  timeframe: string;
  prediction_id: number;
  arth_status: string;
  brain_stats: BrainStats;
}

export interface BrainStats {
  total_predictions: number;
  resolved_predictions: number;
  total_patterns: number;
  active_rules: number;
  overall_accuracy: number;
}

export interface BacktestResult {
  symbol: string;
  strategy: string;
  period: { start: string; end: string };
  metrics: {
    total_trades: number;
    winning_trades: number;
    losing_trades: number;
    win_rate: number;
    avg_profit: number;
    avg_loss: number;
    profit_factor: number;
    total_return: number;
    max_drawdown: number;
    sharpe_ratio: number;
    avg_holding_days: number;
    best_trade: number;
    worst_trade: number;
  };
  trades: Array<{
    symbol: string;
    type: string;
    entry_price: number;
    exit_price: number;
    entry_date: string;
    exit_date: string;
    pnl_percent: number;
    exit_reason: string;
  }>;
  total_trades: number;
}

export interface ChatResponse {
  response: string;
  timestamp: string;
  arth_status: string;
}

export interface ProviderStatus {
  provider: string;
  available: boolean;
  model: string;
  speed: string;
}
