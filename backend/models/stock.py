"""
AI Trader - Stock Data Models
Phase 1: Core data structures
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class SignalType(str, Enum):
    """Trading signal types"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class TrendType(str, Enum):
    """Trend direction types"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class PatternType(str, Enum):
    """Candlestick pattern types"""
    HAMMER = "Hammer"
    SHOOTING_STAR = "Shooting Star"
    BULLISH_ENGULFING = "Bullish Engulfing"
    BEARISH_ENGULFING = "Bearish Engulfing"
    DOJI = "Doji"
    MORNING_STAR = "Morning Star"
    EVENING_STAR = "Evening Star"
    NONE = "None"


class StockInfo(BaseModel):
    """Basic stock information"""
    symbol: str = Field(..., description="Stock symbol")
    name: str = Field(..., description="Company name")
    exchange: str = Field(default="NSE", description="Exchange")
    
    # Price Data
    current_price: float
    previous_close: float
    change: float
    change_percent: float
    
    # OHLC
    open: float
    high: float
    low: float
    volume: int
    
    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # 52W Range
    day_high_52w: Optional[float] = None
    day_low_52w: Optional[float] = None


class TechnicalIndicators(BaseModel):
    """Technical indicators for a stock"""
    # Moving Averages
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    
    # RSI
    rsi: Optional[float] = None
    
    # MACD
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    
    # Support/Resistance
    support: Optional[float] = None
    resistance: Optional[float] = None
    
    # Volume
    avg_volume: Optional[int] = None
    volume_ratio: Optional[float] = None
    
    # Price position
    price_vs_sma20: Optional[float] = None
    price_vs_sma50: Optional[float] = None
    
    # Volatility (ATR) — TRADING FIX: Added for ATR-based stops/targets
    atr: Optional[float] = None


class TradingSignal(BaseModel):
    """Complete trading signal"""
    stock: StockInfo
    indicators: TechnicalIndicators
    
    # Signal
    signal: SignalType = SignalType.HOLD
    confidence: int = Field(0, ge=0, le=100)
    trend: TrendType = TrendType.NEUTRAL
    pattern: PatternType = PatternType.NONE
    
    # Levels
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    risk_reward: Optional[float] = None
    
    # Explanation
    explanation: str = ""
    
    # Metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    signal_strength: str = "MEDIUM"  # WEAK, MEDIUM, STRONG


class SignalsResponse(BaseModel):
    """Response for multiple signals"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    count: int = 0
    buy_count: int = 0
    sell_count: int = 0
    hold_count: int = 0
    signals: List[TradingSignal] = []


class MarketSummary(BaseModel):
    """Market summary"""
    index_name: str
    current_value: float
    change: float
    change_percent: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    timestamp: datetime
    market_status: str  # open, closed


# NSE Stock Lists
NIFTY_50_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "BHARTIARTL",
    "ITC", "KOTAKBANK", "LT", "HINDUNILVR", "SUNPHARMA", "MARUTI", "TATAMOTORS",
    "TATASTEEL", "AXISBANK", "BAJFINANCE", "NTPC", "POWERGRID", "ONGC",
    "COALINDIA", "NESTLEIND", "ULTRACEMCO", "ASIANPAINT", "HCLTECH",
    "WIPRO", "ADANIPORTS", "TITAN", "BAJAJFINSV", "SHRIRAMFIN"
]

NIFTY_BANK_SYMBOLS = [
    "HDFCBANK", "ICICIBANK", "KOTAKBANK", "SBIN", "AXISBANK", "BAJFINANCE",
    "INDUSINDBK", "BANDHANBNK", "IDFCFIRSTB", "AUBANK", "FEDERALBNK",
    "PNB", "CANBK", "BANKOFBARODA", "SBICARD", "TATAINVEST", "M&MFIN"
]
