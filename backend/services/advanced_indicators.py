"""
Advanced Technical Indicators
Bollinger Bands, ATR, Stochastic, ADX, OBV, VWAP, Fibonacci levels
"""

import logging
from typing import Optional, Tuple, List, Dict
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class AdvancedIndicators:
    """Advanced technical analysis indicators"""
    
    def calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: float = 2.0) -> Dict:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            return {}
        
        sma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        
        upper = sma + std_dev * std
        lower = sma - std_dev * std
        bandwidth = (upper - lower) / sma * 100
        pct_b = (prices - lower) / (upper - lower)
        
        return {
            "upper": float(upper.iloc[-1]) if not pd.isna(upper.iloc[-1]) else None,
            "middle": float(sma.iloc[-1]) if not pd.isna(sma.iloc[-1]) else None,
            "lower": float(lower.iloc[-1]) if not pd.isna(lower.iloc[-1]) else None,
            "bandwidth": float(bandwidth.iloc[-1]) if not pd.isna(bandwidth.iloc[-1]) else None,
            "percent_b": float(pct_b.iloc[-1]) if not pd.isna(pct_b.iloc[-1]) else None,
            "squeeze": bool(bandwidth.iloc[-1] < bandwidth.rolling(120).min().iloc[-1]) if len(bandwidth) >= 120 else False,
        }
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> Optional[float]:
        """Calculate Average True Range"""
        if len(df) < period + 1:
            return None
        
        high_low = df['High'] - df['Low']
        high_close = abs(df['High'] - df['Close'].shift())
        low_close = abs(df['Low'] - df['Close'].shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(period).mean()
        
        return float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else None
    
    def calculate_stochastic(self, df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Dict:
        """Calculate Stochastic Oscillator"""
        if len(df) < k_period:
            return {}
        
        low_min = df['Low'].rolling(k_period).min()
        high_max = df['High'].rolling(k_period).max()
        
        k = 100 * (df['Close'] - low_min) / (high_max - low_min)
        d = k.rolling(d_period).mean()
        
        return {
            "k": float(k.iloc[-1]) if not pd.isna(k.iloc[-1]) else None,
            "d": float(d.iloc[-1]) if not pd.isna(d.iloc[-1]) else None,
            "oversold": bool(k.iloc[-1] < 20) if not pd.isna(k.iloc[-1]) else False,
            "overbought": bool(k.iloc[-1] > 80) if not pd.isna(k.iloc[-1]) else False,
        }
    
    def calculate_adx(self, df: pd.DataFrame, period: int = 14) -> Dict:
        """Calculate Average Directional Index"""
        if len(df) < period * 2:
            return {}
        
        high = df['High']
        low = df['Low']
        close = df['Close']
        
        # Calculate +DM and -DM
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        # When +DM > -DM, keep +DM; otherwise 0 (and vice versa)
        plus_dm[plus_dm < minus_dm] = 0
        minus_dm[minus_dm < plus_dm] = 0
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Smoothed values
        atr = tr.rolling(period).mean()
        plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(period).mean()
        
        adx_val = float(adx.iloc[-1]) if not pd.isna(adx.iloc[-1]) else None
        
        return {
            "adx": adx_val,
            "plus_di": float(plus_di.iloc[-1]) if not pd.isna(plus_di.iloc[-1]) else None,
            "minus_di": float(minus_di.iloc[-1]) if not pd.isna(minus_di.iloc[-1]) else None,
            "strong_trend": bool(adx_val and adx_val > 25),
            "trend_direction": "BULLISH" if (plus_di.iloc[-1] > minus_di.iloc[-1]) else "BEARISH" if not pd.isna(plus_di.iloc[-1]) else None,
        }
    
    def calculate_obv(self, df: pd.DataFrame) -> Dict:
        """Calculate On-Balance Volume"""
        if len(df) < 2:
            return {}
        
        obv = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
        obv_ma = obv.rolling(20).mean()
        
        return {
            "obv": float(obv.iloc[-1]),
            "obv_ma20": float(obv_ma.iloc[-1]) if not pd.isna(obv_ma.iloc[-1]) else None,
            "divergence": "BULLISH" if (obv.iloc[-1] > obv_ma.iloc[-1] and df['Close'].iloc[-1] < df['Close'].iloc[-5]) else
                         "BEARISH" if (obv.iloc[-1] < obv_ma.iloc[-1] and df['Close'].iloc[-1] > df['Close'].iloc[-5]) else
                         "NONE",
        }
    
    def calculate_vwap(self, df: pd.DataFrame) -> Optional[float]:
        """Calculate Volume Weighted Average Price"""
        if len(df) < 1:
            return None
        
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        cumvol = df['Volume'].cumsum()
        cumtp = (typical_price * df['Volume']).cumsum()
        
        vwap = cumtp / cumvol
        return float(vwap.iloc[-1]) if not pd.isna(vwap.iloc[-1]) else None
    
    def calculate_fibonacci_levels(self, high: float, low: float) -> Dict:
        """Calculate Fibonacci retracement levels"""
        diff = high - low
        return {
            "0.0": round(high, 2),
            "23.6": round(high - diff * 0.236, 2),
            "38.2": round(high - diff * 0.382, 2),
            "50.0": round(high - diff * 0.5, 2),
            "61.8": round(high - diff * 0.618, 2),
            "78.6": round(high - diff * 0.786, 2),
            "100.0": round(low, 2),
        }
    
    def calculate_pivot_points(self, high: float, low: float, close: float) -> Dict:
        """Calculate traditional pivot points"""
        pivot = (high + low + close) / 3
        
        return {
            "pivot": round(pivot, 2),
            "r1": round(2 * pivot - low, 2),
            "r2": round(pivot + (high - low), 2),
            "r3": round(high + 2 * (pivot - low), 2),
            "s1": round(2 * pivot - high, 2),
            "s2": round(pivot - (high - low), 2),
            "s3": round(low - 2 * (high - pivot), 2),
        }
    
    def calculate_ema_cross_signals(self, prices: pd.Series) -> Dict:
        """Calculate multiple EMA crossover signals"""
        ema_9 = prices.ewm(span=9).mean()
        ema_21 = prices.ewm(span=21).mean()
        ema_50 = prices.ewm(span=50).mean()
        
        signals = {
            "ema_9": float(ema_9.iloc[-1]) if not pd.isna(ema_9.iloc[-1]) else None,
            "ema_21": float(ema_21.iloc[-1]) if not pd.isna(ema_21.iloc[-1]) else None,
            "ema_50": float(ema_50.iloc[-1]) if not pd.isna(ema_50.iloc[-1]) else None,
        }
        
        # Check for crossovers
        if len(prices) >= 2:
            prev_9 = ema_9.iloc[-2]
            prev_21 = ema_21.iloc[-2]
            curr_9 = ema_9.iloc[-1]
            curr_21 = ema_21.iloc[-1]
            
            if prev_9 <= prev_21 and curr_9 > curr_21:
                signals['cross'] = 'BULLISH_CROSS'
            elif prev_9 >= prev_21 and curr_9 < curr_21:
                signals['cross'] = 'BEARISH_CROSS'
            else:
                signals['cross'] = 'NONE'
        
        # Trend alignment
        if all(v is not None for v in [signals['ema_9'], signals['ema_21'], signals['ema_50']]):
            if signals['ema_9'] > signals['ema_21'] > signals['ema_50']:
                signals['alignment'] = 'STRONG_BULLISH'
            elif signals['ema_9'] < signals['ema_21'] < signals['ema_50']:
                signals['alignment'] = 'STRONG_BEARISH'
            else:
                signals['alignment'] = 'MIXED'
        
        return signals
    
    def get_all_advanced(self, df: pd.DataFrame) -> Dict:
        """Calculate all advanced indicators at once"""
        if df is None or df.empty or len(df) < 20:
            return {}
        
        close = df['Close']
        high_val = float(df['High'].tail(20).max())
        low_val = float(df['Low'].tail(20).min())
        last_close = float(close.iloc[-1])
        last_high = float(df['High'].iloc[-1])
        last_low = float(df['Low'].iloc[-1])
        
        return {
            "bollinger": self.calculate_bollinger_bands(close),
            "atr": self.calculate_atr(df),
            "stochastic": self.calculate_stochastic(df),
            "adx": self.calculate_adx(df),
            "obv": self.calculate_obv(df),
            "vwap": self.calculate_vwap(df),
            "fibonacci": self.calculate_fibonacci_levels(high_val, low_val),
            "pivot_points": self.calculate_pivot_points(last_high, last_low, last_close),
            "ema_cross": self.calculate_ema_cross_signals(close),
        }


# Singleton
advanced_indicators = AdvancedIndicators()
