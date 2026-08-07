"""
ARTH's Analyzer - Enhanced analysis with AI and pattern recognition
Combines rule-based analysis with AI insights
"""

import logging
from typing import Dict, Optional, Tuple, List, Any
import pandas as pd
import numpy as np

from models.stock import TechnicalIndicators, StockInfo, SignalType, TrendType, PatternType
from ai_agent.brain import brain
from ai_agent.prompts import SIGNAL_ANALYSIS_PROMPT, CHART_ANALYSIS_PROMPT, PROBABILITY_CALCULATION_PROMPT

logger = logging.getLogger(__name__)


class ArthAnalyzer:
    """Enhanced analyzer combining rule-based and AI analysis"""
    
    def __init__(self):
        self.brain = brain
    
    def get_learned_context(self) -> Tuple[str, str]:
        """Get ARTH's learned patterns and rules as context for AI prompts"""
        # Top patterns
        patterns = self.brain.get_top_patterns(min_uses=3)
        if patterns:
            pattern_text = "\n".join([
                f"- {p['pattern_name']}: {p['success_rate']:.0f}% success ({p['total_uses']} uses)"
                for p in patterns[:10]
            ])
        else:
            pattern_text = "No patterns learned yet. ARTH will learn from this analysis."
        
        # Active rules
        rules = self.brain.get_active_rules()
        if rules:
            rules_text = "\n".join([
                f"- {r['rule_name']}: confidence={r['confidence_score']:.2f}"
                for r in rules[:10]
            ])
        else:
            rules_text = "No active rules yet. Learning from scratch."
        
        return pattern_text, rules_text
    
    def enhance_signal_with_ai(self, stock: StockInfo, indicators: TechnicalIndicators,
                               rule_signal: SignalType, rule_confidence: int,
                               ai_result: Dict) -> Dict:
        """Combine rule-based signal with AI analysis"""
        
        if not ai_result:
            return {
                "signal": rule_signal.value,
                "confidence": rule_confidence,
                "source": "rule-based",
                "ai_enhanced": False
            }
        
        ai_signal = ai_result.get("signal", rule_signal.value).upper()
        ai_confidence = ai_result.get("confidence", rule_confidence)
        
        # Blend AI and rule-based confidence
        # Give more weight to AI as it learns, start with rule-based heavy
        stats = self.brain.get_stats()
        total_predictions = stats.get('total_predictions', 0)
        
        if total_predictions < 20:
            # Early stage: trust rules more
            blended_confidence = int(rule_confidence * 0.7 + ai_confidence * 0.3)
        elif total_predictions < 100:
            # Learning stage: balanced
            blended_confidence = int(rule_confidence * 0.5 + ai_confidence * 0.5)
        else:
            # Mature: trust AI more
            accuracy = stats.get('overall_accuracy', 50)
            ai_weight = min(0.8, 0.5 + accuracy / 200)
            blended_confidence = int(rule_confidence * (1 - ai_weight) + ai_confidence * ai_weight)
        
        # If AI and rules agree, boost confidence
        if ai_signal == rule_signal.value:
            blended_confidence = min(95, blended_confidence + 5)
        # If they disagree, reduce confidence
        elif ai_signal != "HOLD" and rule_signal.value != "HOLD":
            blended_confidence = max(30, blended_confidence - 10)
        
        return {
            "signal": ai_signal if ai_confidence > blended_confidence else rule_signal.value,
            "confidence": blended_confidence,
            "source": "ai-enhanced",
            "ai_enhanced": True,
            "ai_provider": ai_result.get('_provider', 'unknown'),
            "ai_reasoning": ai_result.get('reasoning', ''),
            "ai_entry": ai_result.get('entry_price'),
            "ai_target": ai_result.get('target_price'),
            "ai_stop_loss": ai_result.get('stop_loss'),
            "key_factors": ai_result.get('key_factors', []),
            "risks": ai_result.get('risks', []),
            "timeframe": ai_result.get('timeframe', 'MEDIUM'),
            "arth_learning": ai_result.get('arth_learning', ''),
        }
    
    def calculate_probability(self, symbol: str, signal: str, confidence: int,
                            indicators: TechnicalIndicators, stock: StockInfo) -> Dict:
        """Calculate win probability using ARTH's brain"""
        
        # Base probability from confidence
        base_prob = confidence
        
        # Adjust based on historical accuracy for this signal type
        accuracy_by_signal = self.brain.get_signals_by_accuracy(lookback_days=30)
        if signal in accuracy_by_signal:
            historical_rate = accuracy_by_signal[signal]['accuracy']
            base_prob = int(base_prob * 0.6 + historical_rate * 0.4)
        
        # Adjust for trend alignment
        trend_bonus = 0
        if indicators.sma_20 and indicators.sma_50:
            if signal == "BUY" and indicators.sma_20 > indicators.sma_50:
                trend_bonus = 5
            elif signal == "SELL" and indicators.sma_20 < indicators.sma_50:
                trend_bonus = 5
            elif (signal == "BUY" and indicators.sma_20 < indicators.sma_50) or \
                 (signal == "SELL" and indicators.sma_20 > indicators.sma_50):
                trend_bonus = -5
        
        # Volume confirmation
        vol_bonus = 0
        if indicators.volume_ratio:
            if indicators.volume_ratio > 1.5:
                vol_bonus = 5
            elif indicators.volume_ratio < 0.5:
                vol_bonus = -3
        
        # RSI alignment
        rsi_bonus = 0
        if indicators.rsi:
            if signal == "BUY" and indicators.rsi < 35:
                rsi_bonus = 5
            elif signal == "SELL" and indicators.rsi > 65:
                rsi_bonus = 5
        
        final_prob = max(10, min(95, base_prob + trend_bonus + vol_bonus + rsi_bonus))
        
        # Position sizing suggestion
        if final_prob >= 75:
            position = "FULL"
        elif final_prob >= 60:
            position = "HALF"
        elif final_prob >= 45:
            position = "QUARTER"
        else:
            position = "SKIP"
        
        return {
            "symbol": symbol,
            "signal": signal,
            "win_probability": final_prob,
            "confidence_components": {
                "base_confidence": confidence,
                "trend_adjustment": trend_bonus,
                "volume_adjustment": vol_bonus,
                "rsi_adjustment": rsi_bonus,
            },
            "position_size": position,
            "risk_level": "LOW" if final_prob >= 70 else "MEDIUM" if final_prob >= 50 else "HIGH",
        }
    
    def detect_patterns(self, df: pd.DataFrame) -> List[Dict]:
        """Detect candlestick patterns in price data"""
        patterns = []
        
        if len(df) < 5:
            return patterns
        
        open_prices = df['Open'].values
        high = df['High'].values
        low = df['Low'].values
        close = df['Close'].values
        
        # Check last candle
        o, h, l, c = open_prices[-1], high[-1], low[-1], close[-1]
        body = abs(c - o)
        upper_shadow = h - max(o, c)
        lower_shadow = min(o, c) - l
        total_range = h - l
        
        if total_range == 0:
            return patterns
        
        # Hammer (bullish reversal)
        if lower_shadow > body * 2 and upper_shadow < body * 0.5:
            patterns.append({
                "name": "Hammer",
                "type": "bullish_reversal",
                "reliability": 0.65
            })
        
        # Shooting Star (bearish reversal)
        if upper_shadow > body * 2 and lower_shadow < body * 0.5:
            patterns.append({
                "name": "Shooting Star",
                "type": "bearish_reversal",
                "reliability": 0.65
            })
        
        # Doji
        if body < total_range * 0.1:
            patterns.append({
                "name": "Doji",
                "type": "indecision",
                "reliability": 0.5
            })
        
        # Bullish Engulfing
        if len(df) >= 2:
            prev_o, prev_c = open_prices[-2], close[-2]
            if prev_c < prev_o and c > o and o <= prev_c and c >= prev_o:
                patterns.append({
                    "name": "Bullish Engulfing",
                    "type": "bullish_reversal",
                    "reliability": 0.70
                })
        
        # Bearish Engulfing
        if len(df) >= 2:
            prev_o, prev_c = open_prices[-2], close[-2]
            if prev_c > prev_o and c < o and o >= prev_c and c <= prev_o:
                patterns.append({
                    "name": "Bearish Engulfing",
                    "type": "bearish_reversal",
                    "reliability": 0.70
                })
        
        # Morning Star (3-candle bullish)
        if len(df) >= 3:
            c1_body = abs(close[-3] - open_prices[-3])
            c2_body = abs(close[-2] - open_prices[-2])
            c3_body = abs(c - o)
            
            if (close[-3] < open_prices[-3] and  # First candle bearish
                c2_body < c1_body * 0.3 and  # Small middle body
                c > o and c > open_prices[-3]):  # Third candle bullish
                patterns.append({
                    "name": "Morning Star",
                    "type": "bullish_reversal",
                    "reliability": 0.75
                })
        
        # Evening Star (3-candle bearish)
        if len(df) >= 3:
            c1_body = abs(close[-3] - open_prices[-3])
            c2_body = abs(close[-2] - open_prices[-2])
            
            if (close[-3] > open_prices[-3] and
                c2_body < c1_body * 0.3 and
                c < o and c < open_prices[-3]):
                patterns.append({
                    "name": "Evening Star",
                    "type": "bearish_reversal",
                    "reliability": 0.75
                })
        
        return patterns
    
    def multi_timeframe_analysis(self, data: Dict[str, pd.DataFrame]) -> Dict:
        """Analyze across multiple timeframes"""
        results = {}
        
        for timeframe, df in data.items():
            if df is None or df.empty or len(df) < 20:
                continue
            
            close = df['Close']
            sma_20 = close.tail(20).mean()
            current = close.iloc[-1]
            
            # Determine trend
            if current > sma_20 * 1.02:
                trend = "BULLISH"
            elif current < sma_20 * 0.98:
                trend = "BEARISH"
            else:
                trend = "NEUTRAL"
            
            # Momentum
            momentum = ((current - close.iloc[-5]) / close.iloc[-5] * 100) if len(close) >= 5 else 0
            
            results[timeframe] = {
                "trend": trend,
                "momentum": round(momentum, 2),
                "price_vs_sma20": round((current - sma_20) / sma_20 * 100, 2),
            }
        
        # Overall alignment
        if results:
            trends = [r["trend"] for r in results.values()]
            if all(t == "BULLISH" for t in trends):
                alignment = "STRONG_BULLISH"
            elif all(t == "BEARISH" for t in trends):
                alignment = "STRONG_BEARISH"
            elif trends.count("BULLISH") > trends.count("BEARISH"):
                alignment = "MILD_BULLISH"
            elif trends.count("BEARISH") > trends.count("BULLISH"):
                alignment = "MILD_BEARISH"
            else:
                alignment = "MIXED"
        else:
            alignment = "UNKNOWN"
        
        return {
            "timeframes": results,
            "alignment": alignment
        }
