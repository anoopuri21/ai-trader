"""
AI Trader — Signal Generator Service

Trading Logic Fixes (vs previous version):
  1. RSI is now CONTEXTUAL — not blindly contrarian. In uptrend, high RSI
     confirms momentum. In downtrend, low RSI confirms bearish.
  2. MACD now detects CROSSOVER EVENTS, not just state.
  3. Stop-loss uses ATR (volatility-adjusted), not fixed 1.5%.
  4. Target uses ATR too, maintaining proper R:R ratio.
  5. Confidence uses weighted multi-factor scoring with proper normalization.
  6. Market context (index trend) is factored into every signal.
  7. Volume confirms direction, not independently signals.
  8. Support/resistance uses proper swing highs/lows, not 20-day range.

All changes are annotated with TRADING FIX comments.
"""

import logging
import asyncio
from datetime import datetime
from typing import List, Optional, Tuple

from config import settings
from models.stock import (
    StockInfo, TechnicalIndicators, TradingSignal, SignalType,
    TrendType, PatternType, SignalsResponse, NIFTY_50_SYMBOLS, NIFTY_BANK_SYMBOLS,
)
from services.price_fetcher import price_fetcher
from services.indicators import indicators

logger = logging.getLogger(__name__)


class SignalGenerator:
    """
    Generates trading signals using proper technical analysis.
    
    Signal determination uses weighted multi-factor scoring:
      - Trend alignment (SMA structure): weight 3
      - RSI (contextual): weight 2
      - MACD crossover: weight 2
      - Support/Resistance proximity: weight 2
      - Volume confirmation: weight 1
      - Market breadth: weight 2
      - Pattern detection: weight 1
    
    Total possible score: 13. Signal is determined by score threshold.
    """
    
    def __init__(self):
        self.min_confidence = settings.min_signal_confidence
        self.rsi_oversold = settings.rsi_oversold
        self.rsi_overbought = settings.rsi_overbought
        self.atr_stop_mult = settings.atr_stop_multiplier
        self.atr_target_mult = settings.atr_target_multiplier
        self.max_stop_pct = settings.max_stop_pct
        self.min_stop_pct = settings.min_stop_pct
        self.max_target_pct = settings.max_target_pct
        self.min_rr = settings.min_rr_ratio
    
    async def generate_signal(self, symbol: str, df_override=None, stock_override=None) -> Optional[TradingSignal]:
        """
        Generate complete trading signal for a symbol.
        
        Args:
            symbol: Stock symbol
            df_override: Pre-fetched historical DataFrame (avoids double-fetch)
            stock_override: Pre-fetched StockInfo (avoids double-fetch)
        """
        try:
            # TRADING FIX #7: Accept pre-fetched data to avoid double-fetch
            stock = stock_override or await price_fetcher.get_price(symbol)
            if not stock:
                return None
            
            df = df_override or await price_fetcher.get_historical_data(symbol)
            if df is None or df.empty:
                return None
            
            # Calculate indicators
            ind = indicators.calculate_all(df)
            
            # TRADING FIX #6: Get market context
            market_trend = await self._get_market_context()
            
            # Calculate ATR for volatility-adjusted levels
            atr = self._calculate_atr(df)
            
            # Analyze and generate signal
            signal, trend, pattern, confidence, score_detail = self._analyze(
                stock, ind, df, atr, market_trend
            )
            
            # TRADING FIX #3, #4: ATR-based levels instead of fixed %
            entry, target, stop, rr = self._calculate_levels(
                stock.current_price, signal, ind, atr
            )
            
            explanation = self._generate_explanation(
                stock, ind, signal, trend, pattern, confidence, score_detail, market_trend
            )
            
            return TradingSignal(
                stock=stock,
                indicators=ind,
                signal=signal,
                confidence=confidence,
                trend=trend,
                pattern=pattern,
                entry_price=entry,
                target_price=target,
                stop_loss=stop,
                risk_reward=rr,
                explanation=explanation,
                generated_at=datetime.utcnow(),
                signal_strength=self._get_strength(confidence),
            )
            
        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}")
            return None
    
    async def generate_all_signals(
        self,
        symbols: List[str] = None,
        index: str = "nifty50",
    ) -> SignalsResponse:
        """Generate signals for all specified symbols."""
        if symbols is None:
            symbols = NIFTY_BANK_SYMBOLS if index == "niftybank" else NIFTY_50_SYMBOLS
        
        symbols = list(set(symbols))
        tasks = [self.generate_signal(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        signals = [r for r in results if isinstance(r, TradingSignal)]
        
        buy_count = sum(1 for s in signals if s.signal == SignalType.BUY)
        sell_count = sum(1 for s in signals if s.signal == SignalType.SELL)
        hold_count = sum(1 for s in signals if s.signal == SignalType.HOLD)
        
        return SignalsResponse(
            timestamp=datetime.utcnow(),
            count=len(signals),
            buy_count=buy_count,
            sell_count=sell_count,
            hold_count=hold_count,
            signals=signals,
        )
    
    # ═══════════════════════════════════════════════════════════════
    # CORE ANALYSIS — Weighted Multi-Factor Scoring
    # ═══════════════════════════════════════════════════════════════
    
    def _analyze(
        self,
        stock: StockInfo,
        ind: TechnicalIndicators,
        df,
        atr: Optional[float],
        market_trend: str,
    ) -> Tuple[SignalType, TrendType, PatternType, int, dict]:
        """
        Weighted multi-factor signal analysis.
        
        Each factor contributes a score from -max_weight to +max_weight.
        Positive = bullish, negative = bearish.
        
        Returns: (signal, trend, pattern, confidence, score_detail)
        """
        scores = {}
        max_possible = 0
        
        # ── 1. TREND (weight: 3) ──────────────────────────────────
        trend_score, trend = self._score_trend(ind, stock.current_price)
        scores["trend"] = trend_score
        max_possible += 3
        
        # ── 2. RSI — CONTEXTUAL (weight: 2) ──────────────────────
        # TRADING FIX #1: RSI is contextual, not blindly contrarian
        rsi_score = self._score_rsi_contextual(ind.rsi, trend)
        scores["rsi"] = rsi_score
        max_possible += 2
        
        # ── 3. MACD CROSSOVER (weight: 2) ────────────────────────
        # TRADING FIX #6: Detect crossover events, not just state
        macd_score = self._score_macd_crossover(ind, df)
        scores["macd"] = macd_score
        max_possible += 2
        
        # ── 4. SUPPORT/RESISTANCE (weight: 2) ────────────────────
        sr_score, pattern = self._score_support_resistance(stock, ind, df)
        scores["sr"] = sr_score
        max_possible += 2
        
        # ── 5. VOLUME CONFIRMATION (weight: 1) ───────────────────
        # TRADING FIX #7: Volume confirms, doesn't independently signal
        vol_score = self._score_volume(ind, stock, trend)
        scores["volume"] = vol_score
        max_possible += 1
        
        # ── 6. MARKET CONTEXT (weight: 2) ────────────────────────
        # TRADING FIX #6: Factor in market trend
        market_score = self._score_market_context(market_trend)
        scores["market"] = market_score
        max_possible += 2
        
        # ── 7. CANDLESTICK PATTERN (weight: 1) ──────────────────
        pattern_score = self._score_pattern(pattern)
        scores["pattern"] = pattern_score
        max_possible += 1
        
        # ── AGGREGATE ────────────────────────────────────────────
        # TRADING FIX #2: Proper confidence normalization
        total_score = sum(scores.values())
        
        # Normalize to -100..+100 range, then map to confidence
        # Score ranges from -max_possible to +max_possible
        normalized = (total_score / max_possible) * 100 if max_possible > 0 else 0
        
        # Determine signal
        if normalized >= 25:
            signal = SignalType.BUY
            # Confidence: 50 (at threshold) to 95 (at max)
            confidence = int(50 + (normalized - 25) / 75 * 45)
        elif normalized <= -25:
            signal = SignalType.SELL
            confidence = int(50 + (abs(normalized) - 25) / 75 * 45)
        else:
            signal = SignalType.HOLD
            confidence = int(50 - abs(normalized) * 0.5)  # 50 at zero, lower near threshold
        
        confidence = max(20, min(95, confidence))
        
        return signal, trend, pattern, confidence, scores
    
    # ─── SCORING FUNCTIONS ───────────────────────────────────────
    
    def _score_trend(self, ind: TechnicalIndicators, price: float) -> Tuple[int, TrendType]:
        """
        Score trend alignment using SMA structure.
        Weight: 3 (max contribution: ±3)
        """
        score = 0
        
        # SMA alignment (Golden/Death Cross logic)
        if ind.sma_20 and ind.sma_50:
            if ind.sma_20 > ind.sma_50:
                score += 1  # Short-term bullish
                if price > ind.sma_20:
                    score += 1  # Price confirms
            else:
                score -= 1
                if price < ind.sma_20:
                    score -= 1
        
        # Long-term trend
        if ind.sma_50 and ind.sma_200:
            if ind.sma_50 > ind.sma_200:
                score += 1  # Secular uptrend
            elif ind.sma_50 < ind.sma_200:
                score -= 1  # Secular downtrend
        
        # Clamp to [-3, 3]
        score = max(-3, min(3, score))
        
        if score >= 2:
            trend = TrendType.BULLISH
        elif score <= -2:
            trend = TrendType.BEARISH
        else:
            trend = TrendType.NEUTRAL
        
        return score, trend
    
    def _score_rsi_contextual(self, rsi: Optional[float], trend: TrendType) -> int:
        """
        TRADING FIX #1: Contextual RSI analysis.
        
        Previous logic: RSI < 30 = BUY (+2), RSI > 70 = SELL (-2)
        This was CONTRARIAN and wrong in trending markets.
        
        New logic:
          - In BULLISH trend: RSI 40-70 = momentum continuation (bullish)
                              RSI < 30 = oversold in uptrend = strong BUY
                              RSI > 80 = exhausted = caution
          - In BEARISH trend: RSI 30-60 = momentum continuation (bearish)
                              RSI > 70 = overbought in downtrend = strong SELL
                              RSI < 20 = exhausted = caution
          - In NEUTRAL: Traditional contrarian (oversold=buy, overbought=sell)
        
        Weight: 2 (max: ±2)
        """
        if rsi is None:
            return 0
        
        if trend == TrendType.BULLISH:
            # In uptrend, RSI 50-70 confirms momentum
            if rsi < 30:
                return 2   # Deep oversold in uptrend — strong buy opportunity
            elif 40 <= rsi <= 70:
                return 1   # Healthy momentum continuation
            elif rsi > 80:
                return -1  # Severely exhausted — pullback likely
            elif rsi > 70:
                return 0   # Overbought but trend is up — neutral
            else:
                return -1  # RSI < 40 in "uptrend" — trend may be failing
        
        elif trend == TrendType.BEARISH:
            # In downtrend, RSI 30-50 confirms momentum
            if rsi > 70:
                return -2  # Overbought in downtrend — strong sell
            elif 30 <= rsi <= 50:
                return -1  # Bearish momentum continuation
            elif rsi < 20:
                return 1   # Deeply oversold — bounce possible
            elif rsi < 30:
                return 0   # Oversold but trend is down — neutral
            else:
                return 1   # RSI > 50 in "downtrend" — trend may be reversing
        
        else:  # NEUTRAL — traditional contrarian
            if rsi < self.rsi_oversold:
                return 2   # Oversold — potential bounce
            elif rsi > self.rsi_overbought:
                return -2  # Overbought — potential pullback
            elif rsi < 40:
                return 1   # Approaching oversold
            elif rsi > 60:
                return -1  # Approaching overbought
            return 0
    
    def _score_macd_crossover(self, ind: TechnicalIndicators, df) -> int:
        """
        TRADING FIX #6: Detect MACD CROSSOVER EVENTS, not just state.
        
        Previous logic: macd > macd_signal → bullish. This is wrong
        because MACD can be above signal line for weeks — that's not a signal.
        
        New logic: Detect the actual crossover event (MACD crossing signal)
        within the last 2-3 bars. Fresh crossovers are more actionable.
        
        Weight: 2 (max: ±2)
        """
        if ind.macd is None or ind.macd_signal is None:
            return 0
        
        # Check for fresh crossover (last 3 bars)
        if df is not None and len(df) >= 4:
            try:
                close = df["Close"]
                ema_fast = close.ewm(span=12, adjust=False).mean()
                ema_slow = close.ewm(span=26, adjust=False).mean()
                macd_line = ema_fast - ema_slow
                signal_line = macd_line.ewm(span=9, adjust=False).mean()
                
                # Current and previous MACD vs Signal
                curr_diff = macd_line.iloc[-1] - signal_line.iloc[-1]
                prev_diff = macd_line.iloc[-2] - signal_line.iloc[-2]
                prev2_diff = macd_line.iloc[-3] - signal_line.iloc[-3] if len(macd_line) >= 3 else 0
                
                # Bullish crossover: MACD crosses above signal
                if prev_diff <= 0 and curr_diff > 0:
                    return 2  # Fresh bullish crossover — strong signal
                elif prev2_diff <= 0 and prev_diff > 0:
                    return 1  # Recent bullish crossover (1-2 bars ago)
                
                # Bearish crossover: MACD crosses below signal
                if prev_diff >= 0 and curr_diff < 0:
                    return -2  # Fresh bearish crossover
                elif prev2_diff >= 0 and prev_diff < 0:
                    return -1  # Recent bearish crossover
                
                # No fresh crossover — check momentum
                if curr_diff > 0 and curr_diff > prev_diff:
                    return 1  # MACD expanding above signal (bullish momentum)
                elif curr_diff < 0 and curr_diff < prev_diff:
                    return -1  # MACD expanding below signal (bearish momentum)
                
            except Exception:
                pass
        
        # Fallback: just check state
        if ind.macd > ind.macd_signal:
            return 1 if (ind.macd_histogram and ind.macd_histogram > 0) else 0
        else:
            return -1 if (ind.macd_histogram and ind.macd_histogram < 0) else 0
    
    def _score_support_resistance(self, stock: StockInfo, ind: TechnicalIndicators, df) -> Tuple[int, PatternType]:
        """
        Score based on proximity to support/resistance.
        
        TRADING FIX #5: Use swing highs/lows, not just 20-day range.
        Also: don't assign candlestick patterns just because price is near S/R.
        
        Weight: 2 (max: ±2)
        """
        score = 0
        pattern = PatternType.NONE
        
        if not (ind.resistance and ind.support):
            return 0, pattern
        
        range_size = ind.resistance - ind.support
        if range_size <= 0:
            return 0, pattern
        
        # Position within range (0 = at support, 1 = at resistance)
        price_pos = (stock.current_price - ind.support) / range_size
        
        if price_pos < 0.10:
            score = 2   # Very near support — potential bounce zone
        elif price_pos < 0.20:
            score = 1   # Near support
        elif price_pos > 0.90:
            score = -2  # Very near resistance — potential rejection
        elif price_pos > 0.80:
            score = -1  # Near resistance
        
        # Don't assign candlestick pattern here — it's detected separately
        
        return score, pattern
    
    def _score_volume(self, ind: TechnicalIndicators, stock: StockInfo, trend: TrendType) -> int:
        """
        TRADING FIX #7: Volume CONFIRMS direction, doesn't independently signal.
        
        Previous logic: high volume = +1 to buy, low volume = -1.
        This was wrong because high volume on a down day is bearish!
        
        New logic: Volume confirms the TREND direction.
          - High volume + bullish trend = confirms (+1)
          - High volume + bearish trend = confirms (-1)
          - Low volume = reduces conviction (0)
          - High volume + price change in trend direction = strong confirm (+1/-1)
        
        Weight: 1 (max: ±1)
        """
        if ind.volume_ratio is None:
            return 0
        
        if ind.volume_ratio > 1.5:
            # High volume — confirms whatever the trend is
            if trend == TrendType.BULLISH and stock.change_percent > 0:
                return 1   # High volume buying — strong confirmation
            elif trend == TrendType.BEARISH and stock.change_percent < 0:
                return -1  # High volume selling — strong confirmation
            elif stock.change_percent > 1:
                return 1   # High volume rally (even in neutral)
            elif stock.change_percent < -1:
                return -1  # High volume selloff
            return 0
        elif ind.volume_ratio < 0.5:
            # Very low volume — thin market, unreliable moves
            return 0
        
        return 0
    
    def _score_market_context(self, market_trend: str) -> int:
        """
        TRADING FIX #6: Factor in overall market trend.
        
        If Nifty is strongly bearish, individual stock BUY signals
        have much lower probability of success.
        
        Weight: 2 (max: ±2)
        """
        if market_trend == "STRONG_BULLISH":
            return 2
        elif market_trend == "BULLISH":
            return 1
        elif market_trend == "STRONG_BEARISH":
            return -2
        elif market_trend == "BEARISH":
            return -1
        return 0
    
    def _score_pattern(self, pattern: PatternType) -> int:
        """Score based on detected candlestick pattern. Weight: 1."""
        bullish_patterns = {PatternType.HAMMER, PatternType.BULLISH_ENGULFING, PatternType.MORNING_STAR}
        bearish_patterns = {PatternType.SHOOTING_STAR, PatternType.BEARISH_ENGULFING, PatternType.EVENING_STAR}
        
        if pattern in bullish_patterns:
            return 1
        elif pattern in bearish_patterns:
            return -1
        return 0
    
    # ─── MARKET CONTEXT ──────────────────────────────────────────
    
    async def _get_market_context(self) -> str:
        """
        Get current market trend from Nifty 50 index.
        Returns: STRONG_BULLISH, BULLISH, NEUTRAL, BEARISH, STRONG_BEARISH
        """
        try:
            from services.price_fetcher import price_fetcher
            indices = await price_fetcher.get_index_data()
            
            if "^NSEI" not in indices:
                return "NEUTRAL"
            
            change_pct = indices["^NSEI"].get("change_percent", 0)
            
            if change_pct > 1.5:
                return "STRONG_BULLISH"
            elif change_pct > 0.3:
                return "BULLISH"
            elif change_pct < -1.5:
                return "STRONG_BEARISH"
            elif change_pct < -0.3:
                return "BEARISH"
            return "NEUTRAL"
            
        except Exception:
            return "NEUTRAL"
    
    # ─── ATR CALCULATION ─────────────────────────────────────────
    
    def _calculate_atr(self, df, period: int = 14) -> Optional[float]:
        """
        Calculate Average True Range for volatility-adjusted levels.
        
        TRADING FIX #3, #4: ATR-based stops/targets instead of fixed %.
        """
        if len(df) < period + 1:
            return None
        
        try:
            high_low = df["High"] - df["Low"]
            high_close = abs(df["High"] - df["Close"].shift())
            low_close = abs(df["Low"] - df["Close"].shift())
            
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.rolling(period).mean()
            
            return float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else None
        except Exception:
            return None
    
    # ─── LEVEL CALCULATION ───────────────────────────────────────
    
    def _calculate_levels(
        self,
        price: float,
        signal: SignalType,
        ind: TechnicalIndicators,
        atr: Optional[float],
    ) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
        """
        Calculate entry, target, stop-loss, and risk-reward ratio.
        
        TRADING FIX #3, #4: ATR-based levels.
        - Stop-loss = Entry ± (ATR × multiplier), capped to [1%, 5%]
        - Target = Entry ± (ATR × multiplier), capped to [1.5× stop, 10%]
        - Ensures minimum R:R of 1.5:1
        """
        if signal == SignalType.HOLD:
            return None, None, None, None
        
        try:
            if atr and atr > 0:
                # ATR-based stops
                stop_distance = atr * self.atr_stop_mult
                target_distance = atr * self.atr_target_mult
                
                # Convert to percentage and apply caps
                stop_pct = max(self.min_stop_pct, min(self.max_stop_pct, stop_distance / price))
                target_pct = max(stop_pct * self.min_rr, min(self.max_target_pct, target_distance / price))
            else:
                # Fallback: use S/R-based levels or default
                if ind.resistance and ind.support and price > 0:
                    range_size = ind.resistance - ind.support
                    stop_pct = max(self.min_stop_pct, min(self.max_stop_pct, range_size / price * 0.3))
                    target_pct = max(stop_pct * self.min_rr, min(self.max_target_pct, range_size / price * 0.7))
                else:
                    # Last resort defaults (wider than before)
                    stop_pct = 0.02   # 2% stop
                    target_pct = 0.04  # 4% target
            
            if signal == SignalType.BUY:
                entry = price
                target = price * (1 + target_pct)
                stop = price * (1 - stop_pct)
            else:  # SELL
                entry = price
                target = price * (1 - target_pct)
                stop = price * (1 + stop_pct)
            
            risk = abs(entry - stop)
            reward = abs(target - entry)
            rr = round(reward / risk, 2) if risk > 0 else None
            
            return round(entry, 2), round(target, 2), round(stop, 2), rr
            
        except Exception:
            return None, None, None, None
    
    # ─── EXPLANATION ─────────────────────────────────────────────
    
    def _generate_explanation(
        self, stock, ind, signal, trend, pattern, confidence, scores, market_trend
    ) -> str:
        """Generate human-readable explanation of the signal."""
        parts = []
        
        # Trend
        if trend == TrendType.BULLISH:
            sma_info = f"SMA20: ₹{ind.sma_20:.0f}" if ind.sma_20 else ""
            parts.append(f"Bullish trend ({sma_info})")
        elif trend == TrendType.BEARISH:
            parts.append("Bearish trend (price below moving averages)")
        else:
            parts.append("No clear trend — price consolidating")
        
        # RSI
        if ind.rsi:
            if ind.rsi < 30:
                parts.append(f"RSI deeply oversold ({ind.rsi:.0f})")
            elif ind.rsi > 70:
                parts.append(f"RSI overbought ({ind.rsi:.0f})")
            elif 40 <= ind.rsi <= 60:
                parts.append(f"RSI neutral ({ind.rsi:.0f})")
            else:
                parts.append(f"RSI {ind.rsi:.0f}")
        
        # MACD
        if ind.macd and ind.macd_signal:
            if ind.macd > ind.macd_signal:
                parts.append("MACD above signal line")
            else:
                parts.append("MACD below signal line")
        
        # Market context
        if market_trend != "NEUTRAL":
            parts.append(f"Market: {market_trend.replace('_', ' ').title()}")
        
        # Pattern
        if pattern != PatternType.NONE:
            parts.append(f"Pattern: {pattern.value}")
        
        # Signal summary
        emoji = "🟢" if signal == SignalType.BUY else "🔴" if signal == SignalType.SELL else "🟡"
        parts.append(f"{emoji} {signal.value} | Confidence: {confidence}%")
        
        return ". ".join(parts)
    
    def _get_strength(self, confidence: int) -> str:
        if confidence >= 75:
            return "STRONG"
        elif confidence >= 60:
            return "MEDIUM"
        return "WEAK"


# Singleton
signal_generator = SignalGenerator()

# Need pandas for ATR calculation
import pandas as pd
