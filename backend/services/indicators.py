"""
AI Trader - Technical Indicators Service
Phase 1: Rule-based technical analysis
"""

import logging
from typing import Optional, Tuple
import pandas as pd
import numpy as np

from config import settings
from models.stock import TechnicalIndicators

logger = logging.getLogger(__name__)


class Indicators:
    """Calculate technical indicators for stock analysis"""
    
    def __init__(self):
        self.rsi_period = settings.rsi_period
        self.sma_short = settings.sma_short
        self.sma_mid = settings.sma_mid
        self.sma_long = settings.sma_long
        self.macd_fast = settings.macd_fast
        self.macd_slow = settings.macd_slow
        self.macd_signal = settings.macd_signal
    
    def calculate_all(self, df: pd.DataFrame) -> TechnicalIndicators:
        """Calculate all technical indicators from OHLC data"""
        if df is None or df.empty:
            return TechnicalIndicators()
        
        indicators = TechnicalIndicators()
        
        # Moving Averages
        indicators.sma_20 = self._calculate_sma(df['Close'], self.sma_short)
        indicators.sma_50 = self._calculate_sma(df['Close'], self.sma_mid)
        indicators.sma_200 = self._calculate_sma(df['Close'], self.sma_long)
        
        # RSI
        indicators.rsi = self._calculate_rsi(df['Close'])
        
        # MACD
        macd, macd_sig, macd_hist = self._calculate_macd(df['Close'])
        indicators.macd = macd
        indicators.macd_signal = macd_sig
        indicators.macd_histogram = macd_hist
        
        # Support & Resistance
        support, resistance = self._calculate_support_resistance(df)
        indicators.support = support
        indicators.resistance = resistance
        
        # Volume analysis
        indicators.avg_volume = int(df['Volume'].tail(20).mean()) if len(df) >= 20 else int(df['Volume'].mean())
        indicators.volume_ratio = self._calculate_volume_ratio(df)
        
        # Price position
        if indicators.sma_20:
            indicators.price_vs_sma20 = ((df['Close'].iloc[-1] - indicators.sma_20) / indicators.sma_20) * 100
        if indicators.sma_50:
            indicators.price_vs_sma50 = ((df['Close'].iloc[-1] - indicators.sma_50) / indicators.sma_50) * 100
        
        return indicators
    
    def _calculate_sma(self, prices: pd.Series, period: int) -> Optional[float]:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return None
        return float(prices.tail(period).mean())
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> Optional[float]:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return None
        
        try:
            delta = prices.diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None
        except Exception:
            return None
    
    def _calculate_macd(
        self, 
        prices: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Calculate MACD indicator"""
        if len(prices) < slow:
            return None, None, None
        
        try:
            ema_fast = prices.ewm(span=fast, adjust=False).mean()
            ema_slow = prices.ewm(span=slow, adjust=False).mean()
            
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal, adjust=False).mean()
            histogram = macd_line - signal_line
            
            return (
                float(macd_line.iloc[-1]) if not pd.isna(macd_line.iloc[-1]) else None,
                float(signal_line.iloc[-1]) if not pd.isna(signal_line.iloc[-1]) else None,
                float(histogram.iloc[-1]) if not pd.isna(histogram.iloc[-1]) else None
            )
        except Exception:
            return None, None, None
    
    def _calculate_support_resistance(self, df: pd.DataFrame) -> Tuple[Optional[float], Optional[float]]:
        """Calculate support and resistance levels"""
        if len(df) < 20:
            return None, None
        
        try:
            # Recent 20 days high/low
            support = float(df['Low'].tail(20).min())
            resistance = float(df['High'].tail(20).max())
            return support, resistance
        except Exception:
            return None, None
    
    def _calculate_volume_ratio(self, df: pd.DataFrame) -> Optional[float]:
        """Calculate volume ratio (current volume vs 20-day average)"""
        if len(df) < 20:
            return None
        
        try:
            current_volume = df['Volume'].iloc[-1]
            avg_volume = df['Volume'].tail(20).mean()
            return float(current_volume / avg_volume) if avg_volume > 0 else None
        except Exception:
            return None


# Singleton instance
indicators = Indicators()
