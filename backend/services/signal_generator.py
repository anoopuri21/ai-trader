"""
AI Trader - Signal Generator Service
Phase 1: Rule-based BUY/SELL/HOLD signals
"""

import logging
import asyncio
from datetime import datetime
from typing import List, Optional, Tuple

from config import settings
from models.stock import (
    StockInfo, TechnicalIndicators, TradingSignal, SignalType,
    TrendType, PatternType, SignalsResponse, NIFTY_50_SYMBOLS, NIFTY_BANK_SYMBOLS
)
from services.price_fetcher import price_fetcher
from services.indicators import indicators

logger = logging.getLogger(__name__)


class SignalGenerator:
    """
    Generates trading signals based on rule-based technical analysis.
    Phase 1: Pure rule-based, no AI dependency.
    """
    
    def __init__(self):
        self.min_confidence = settings.min_signal_confidence
        self.rsi_oversold = settings.rsi_oversold
        self.rsi_overbought = settings.rsi_overbought
    
    async def generate_signal(self, symbol: str) -> Optional[TradingSignal]:
        """Generate complete trading signal for a symbol"""
        try:
            # Get price data
            stock = await price_fetcher.get_price(symbol)
            if not stock:
                return None
            
            # Get historical data for indicators
            df = await price_fetcher.get_historical_data(symbol)
            if df is None or df.empty:
                return None
            
            # Calculate indicators
            ind = indicators.calculate_all(df)
            
            # Analyze and generate signal
            signal, trend, pattern, confidence = self._analyze(
                stock, ind
            )
            
            # Calculate levels
            entry, target, stop, rr = self._calculate_levels(
                stock.current_price, signal, ind
            )
            
            # Generate explanation
            explanation = self._generate_explanation(
                stock, ind, signal, trend, pattern, confidence
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
                signal_strength=self._get_strength(confidence)
            )
            
        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}")
            return None
    
    async def generate_all_signals(
        self, 
        symbols: List[str] = None,
        index: str = "nifty50"
    ) -> SignalsResponse:
        """Generate signals for all specified symbols"""
        if symbols is None:
            if index == "niftybank":
                symbols = NIFTY_BANK_SYMBOLS
            else:
                symbols = NIFTY_50_SYMBOLS
        
        # Remove duplicates
        symbols = list(set(symbols))
        
        # Generate signals concurrently
        tasks = [self.generate_signal(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        signals = [r for r in results if isinstance(r, TradingSignal)]
        
        # Count by signal type
        buy_count = sum(1 for s in signals if s.signal == SignalType.BUY)
        sell_count = sum(1 for s in signals if s.signal == SignalType.SELL)
        hold_count = sum(1 for s in signals if s.signal == SignalType.HOLD)
        
        return SignalsResponse(
            timestamp=datetime.utcnow(),
            count=len(signals),
            buy_count=buy_count,
            sell_count=sell_count,
            hold_count=hold_count,
            signals=signals
        )
    
    def _analyze(
        self,
        stock: StockInfo,
        ind: TechnicalIndicators
    ) -> Tuple[SignalType, TrendType, PatternType, int]:
        """
        Core rule-based analysis.
        Returns: (Signal, Trend, Pattern, Confidence)
        """
        scores = {"buy": 0, "sell": 0, "hold": 0}
        pattern = PatternType.NONE
        
        # 1. Trend Analysis (Moving Averages)
        trend_score, trend = self._analyze_trend(ind, stock.current_price)
        if trend_score > 0:
            scores["buy"] += trend_score
        elif trend_score < 0:
            scores["sell"] += abs(trend_score)
        else:
            scores["hold"] += 1
        
        # 2. RSI Analysis
        rsi_score = self._analyze_rsi(ind.rsi)
        if rsi_score > 0:
            scores["buy"] += rsi_score
        elif rsi_score < 0:
            scores["sell"] += abs(rsi_score)
        
        # 3. MACD Analysis
        macd_score = self._analyze_macd(ind)
        if macd_score > 0:
            scores["buy"] += macd_score
        elif macd_score < 0:
            scores["sell"] += abs(macd_score)
        
        # 4. Support/Resistance
        sr_score, pattern = self._analyze_support_resistance(stock, ind)
        if sr_score > 0:
            scores["buy"] += sr_score
        elif sr_score < 0:
            scores["sell"] += abs(sr_score)
        
        # 5. Volume confirmation
        vol_score = self._analyze_volume(ind)
        if vol_score > 0:
            scores["buy"] += vol_score
        elif vol_score < 0:
            scores["sell"] += abs(vol_score)
        
        # Determine final signal
        total = scores["buy"] + scores["sell"] + scores["hold"]
        if total == 0:
            total = 1
        
        buy_pct = (scores["buy"] / total) * 100
        sell_pct = (scores["sell"] / total) * 100
        
        # Signal determination
        if buy_pct >= 40 and buy_pct > sell_pct + 10:
            signal = SignalType.BUY
            confidence = int(min(95, 50 + buy_pct - sell_pct))
        elif sell_pct >= 40 and sell_pct > buy_pct + 10:
            signal = SignalType.SELL
            confidence = int(min(95, 50 + sell_pct - buy_pct))
        else:
            signal = SignalType.HOLD
            confidence = int(min(70, 50 + abs(buy_pct - sell_pct)))
        
        return signal, trend, pattern, confidence
    
    def _analyze_trend(self, ind: TechnicalIndicators, price: float) -> Tuple[int, TrendType]:
        """Analyze trend using moving averages"""
        score = 0
        
        if ind.sma_20 and ind.sma_50:
            if ind.sma_20 > ind.sma_50:
                score += 1
                if price > ind.sma_20:
                    score += 1
            else:
                score -= 1
                if price < ind.sma_20:
                    score -= 1
        
        if ind.sma_50 and ind.sma_200:
            if ind.sma_50 > ind.sma_200:
                score += 2  # Long-term bullish
            else:
                score -= 2
        
        if score >= 2:
            return score, TrendType.BULLISH
        elif score <= -2:
            return score, TrendType.BEARISH
        else:
            return score, TrendType.NEUTRAL
    
    def _analyze_rsi(self, rsi: Optional[float]) -> int:
        """Analyze RSI indicator"""
        if rsi is None:
            return 0
        
        if rsi < self.rsi_oversold:
            return 2  # Oversold - potential buy
        elif rsi > self.rsi_overbought:
            return -2  # Overbought - potential sell
        elif rsi < 40:
            return 1
        elif rsi > 60:
            return -1
        return 0
    
    def _analyze_macd(self, ind: TechnicalIndicators) -> int:
        """Analyze MACD indicator"""
        if ind.macd is None or ind.macd_signal is None:
            return 0
        
        if ind.macd > ind.macd_signal:
            if ind.macd_histogram and ind.macd_histogram > 0:
                return 2  # Strong bullish
            return 1
        else:
            if ind.macd_histogram and ind.macd_histogram < 0:
                return -2  # Strong bearish
            return -1
    
    def _analyze_support_resistance(
        self,
        stock: StockInfo,
        ind: TechnicalIndicators
    ) -> Tuple[int, PatternType]:
        """Analyze price relative to support/resistance"""
        score = 0
        pattern = PatternType.NONE
        
        if ind.resistance and ind.support:
            range_size = ind.resistance - ind.support
            if range_size > 0:
                price_pos = (stock.current_price - ind.support) / range_size
                
                if price_pos < 0.15:
                    score = 2  # Near support - potential buy
                    pattern = PatternType.HAMMER
                elif price_pos > 0.85:
                    score = -2  # Near resistance - potential sell
                    pattern = PatternType.SHOOTING_STAR
        
        return score, pattern
    
    def _analyze_volume(self, ind: TechnicalIndicators) -> int:
        """Analyze volume"""
        if ind.volume_ratio is None:
            return 0
        
        if ind.volume_ratio > 1.5:
            return 1  # High volume confirms move
        elif ind.volume_ratio < 0.5:
            return -1
        return 0
    
    def _calculate_levels(
        self,
        price: float,
        signal: SignalType,
        ind: TechnicalIndicators
    ) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
        """Calculate entry, target, stop loss, and risk-reward"""
        if signal == SignalType.HOLD:
            return None, None, None, None
        
        try:
            # Default: 3% target, 1.5% stop
            target_pct = 0.03
            stop_pct = 0.015
            
            # Adjust based on indicators
            if ind.resistance and ind.support:
                range_size = ind.resistance - ind.support
                potential = range_size / price
                target_pct = min(potential * 0.7, 0.05)  # Max 5%
                stop_pct = min(potential * 0.3, 0.02)   # Max 2%
            
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
            rr = reward / risk if risk > 0 else None
            
            return round(entry, 2), round(target, 2), round(stop, 2), round(rr, 2) if rr else None
            
        except Exception:
            return None, None, None, None
    
    def _generate_explanation(
        self,
        stock: StockInfo,
        ind: TechnicalIndicators,
        signal: SignalType,
        trend: TrendType,
        pattern: PatternType,
        confidence: int
    ) -> str:
        """Generate human-readable explanation"""
        parts = []
        
        # Trend
        if trend == TrendType.BULLISH:
            parts.append(f"Bullish trend confirmed (price above SMA20: ₹{ind.sma_20:.0f}, SMA50: ₹{ind.sma_50:.0f})")
        elif trend == TrendType.BEARISH:
            parts.append(f"Bearish trend confirmed (price below SMAs)")
        else:
            parts.append("Price consolidating, no clear trend")
        
        # RSI
        if ind.rsi:
            if ind.rsi < 30:
                parts.append(f"RSI oversold at {ind.rsi:.1f}")
            elif ind.rsi > 70:
                parts.append(f"RSI overbought at {ind.rsi:.1f}")
            else:
                parts.append(f"RSI neutral at {ind.rsi:.1f}")
        
        # MACD
        if ind.macd and ind.macd_signal:
            if ind.macd > ind.macd_signal:
                parts.append("MACD bullish crossover")
            else:
                parts.append("MACD bearish crossover")
        
        # Pattern
        if pattern != PatternType.NONE:
            parts.append(f"Pattern: {pattern.value}")
        
        # Signal summary
        emoji = "🟢" if signal == SignalType.BUY else "🔴" if signal == SignalType.SELL else "🟡"
        parts.append(f"\n{emoji} {signal.value} with {confidence}% confidence")
        
        return ". ".join(parts)
    
    def _get_strength(self, confidence: int) -> str:
        """Determine signal strength"""
        if confidence >= 75:
            return "STRONG"
        elif confidence >= 60:
            return "MEDIUM"
        return "WEAK"


# Singleton instance
signal_generator = SignalGenerator()
