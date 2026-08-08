"""
ARTH — AI Trading Agent

Architecture Fix: Uses centralized DatabaseManager via ArthBrain.
No more separate brain instances. Passes pre-fetched data to signal
generator to avoid double-fetching.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any, List

from ai_agent.brain import ArthBrain
from ai_agent.router import AIRouter
from ai_agent.analyzer import ArthAnalyzer
from ai_agent.prompts import SIGNAL_ANALYSIS_PROMPT, SELF_REFLECTION_PROMPT
from services.price_fetcher import price_fetcher
from services.indicators import indicators
from services.signal_generator import signal_generator
from models.stock import SignalType

logger = logging.getLogger(__name__)


class ArthAgent:
    """
    ARTH — The AI Trading Agent.
    
    Orchestrates analysis, learning, and signal generation.
    Uses centralized database via ArthBrain.
    """
    
    def __init__(self):
        self.brain: Optional[ArthBrain] = None
        self.router: Optional[AIRouter] = None
        self.analyzer: Optional[ArthAnalyzer] = None
        self.status = "initializing"
        self._initialized = False
    
    async def initialize(self):
        """Initialize ARTH and all components."""
        try:
            logger.info("ARTH: Initializing brain...")
            self.brain = ArthBrain()  # Uses centralized DB internally
            
            logger.info("ARTH: Initializing AI router...")
            self.router = AIRouter()
            
            logger.info("ARTH: Initializing analyzer...")
            self.analyzer = ArthAnalyzer(self.brain)
            
            available = self.router.get_available_providers()
            if available:
                self.status = "ready"
                logger.info(f"ARTH: Ready! AI providers: {available}")
            else:
                self.status = "rule-based"
                logger.info("ARTH: No AI providers — rule-based mode")
            
            self._initialized = True
            
            # Resolve pending predictions
            await self._resolve_pending_predictions()
            
        except Exception as e:
            logger.error(f"ARTH initialization error: {e}")
            self.status = "error"
    
    async def shutdown(self):
        if self.brain:
            self.brain.close()
        logger.info("ARTH: Shutdown complete")
    
    async def analyze_stock(self, symbol: str) -> Dict[str, Any]:
        """
        Full ARTH analysis — combines rule-based + AI.
        
        Architecture Fix: Fetches data once, passes to both signal
        generator and indicators (previously fetched 2x).
        """
        if not self._initialized:
            return {"error": "ARTH not initialized"}
        
        # 1. Fetch data ONCE
        stock = await price_fetcher.get_price(symbol)
        if not stock:
            return {"error": f"Could not fetch data for {symbol}"}
        
        df = await price_fetcher.get_historical_data(symbol)
        if df is None or df.empty:
            return {"error": f"No historical data for {symbol}"}
        
        # 2. Calculate indicators (from pre-fetched df)
        ind = indicators.calculate_all(df)
        
        # 3. Generate rule-based signal (pass pre-fetched data)
        rule_signal = await signal_generator.generate_signal(
            symbol, df_override=df, stock_override=stock
        )
        
        # 4. Detect patterns
        patterns = self.analyzer.detect_patterns(df)
        
        # 5. AI analysis (if available)
        ai_result = None
        if self.status == "ready":
            learned_patterns, learned_rules = self.analyzer.get_learned_context()
            
            prompt = SIGNAL_ANALYSIS_PROMPT.format(
                symbol=symbol,
                company_name=stock.name,
                price=stock.current_price,
                change_percent=f"{stock.change_percent:.2f}",
                rsi_period=14,
                rsi=f"{ind.rsi:.1f}" if ind.rsi else "N/A",
                sma20=f"{ind.sma_20:.0f}" if ind.sma_20 else "N/A",
                sma50=f"{ind.sma_50:.0f}" if ind.sma_50 else "N/A",
                sma200=f"{ind.sma_200:.0f}" if ind.sma_200 else "N/A",
                macd=f"{ind.macd:.2f}" if ind.macd else "N/A",
                macd_signal=f"{ind.macd_signal:.2f}" if ind.macd_signal else "N/A",
                macd_hist=f"{ind.macd_histogram:.2f}" if ind.macd_histogram else "N/A",
                support=f"{ind.support:.0f}" if ind.support else "N/A",
                resistance=f"{ind.resistance:.0f}" if ind.resistance else "N/A",
                volume_ratio=f"{ind.volume_ratio:.2f}" if ind.volume_ratio else "N/A",
                learned_patterns=learned_patterns,
                learned_rules=learned_rules,
            )
            
            ai_result = await self.router.analyze(prompt)
        
        # 6. Combine rule-based + AI
        if rule_signal:
            enhanced = self.analyzer.enhance_signal_with_ai(
                stock, ind, rule_signal.signal, rule_signal.confidence, ai_result
            )
        else:
            enhanced = {
                "signal": "HOLD", "confidence": 50,
                "source": "fallback", "ai_enhanced": False,
            }
        
        # 7. Probability
        probability = self.analyzer.calculate_probability(
            symbol, enhanced["signal"], enhanced["confidence"], ind, stock
        )
        
        # 8. Store prediction
        prediction_id = self.brain.store_prediction(
            symbol=symbol,
            signal=enhanced["signal"],
            confidence=enhanced["confidence"],
            entry_price=enhanced.get("ai_entry") or (rule_signal.entry_price if rule_signal else None),
            target_price=enhanced.get("ai_target") or (rule_signal.target_price if rule_signal else None),
            stop_loss=enhanced.get("ai_stop_loss") or (rule_signal.stop_loss if rule_signal else None),
            indicators={"rsi": ind.rsi, "sma_20": ind.sma_20, "sma_50": ind.sma_50, "macd": ind.macd, "volume_ratio": ind.volume_ratio},
            ai_provider=enhanced.get("ai_provider"),
            ai_reasoning=enhanced.get("ai_reasoning"),
            pattern_used=patterns[0]["name"] if patterns else None,
        )
        
        return {
            "symbol": symbol,
            "company_name": stock.name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "price": {
                "current": stock.current_price, "change": stock.change,
                "change_percent": stock.change_percent, "open": stock.open,
                "high": stock.high, "low": stock.low, "volume": stock.volume,
            },
            "indicators": {
                "rsi": ind.rsi, "sma_20": ind.sma_20, "sma_50": ind.sma_50,
                "sma_200": ind.sma_200, "macd": ind.macd, "macd_signal": ind.macd_signal,
                "macd_histogram": ind.macd_histogram, "support": ind.support,
                "resistance": ind.resistance, "volume_ratio": ind.volume_ratio,
            },
            "signal": enhanced["signal"],
            "confidence": enhanced["confidence"],
            "source": enhanced["source"],
            "ai_enhanced": enhanced["ai_enhanced"],
            "ai_provider": enhanced.get("ai_provider"),
            "ai_reasoning": enhanced.get("ai_reasoning", ""),
            "probability": probability,
            "levels": {
                "entry": enhanced.get("ai_entry") or (rule_signal.entry_price if rule_signal else None),
                "target": enhanced.get("ai_target") or (rule_signal.target_price if rule_signal else None),
                "stop_loss": enhanced.get("ai_stop_loss") or (rule_signal.stop_loss if rule_signal else None),
                "risk_reward": rule_signal.risk_reward if rule_signal else None,
            },
            "patterns": patterns,
            "key_factors": enhanced.get("key_factors", []),
            "risks": enhanced.get("risks", []),
            "timeframe": enhanced.get("timeframe", "MEDIUM"),
            "prediction_id": prediction_id,
            "arth_status": self.status,
            "brain_stats": self.brain.get_stats(),
        }
    
    async def chat(self, message: str, context: Dict = None) -> Dict:
        """Chat with ARTH."""
        if not self._initialized:
            return {"response": "ARTH is initializing. Please wait.", "timestamp": datetime.now(timezone.utc).isoformat(), "arth_status": self.status}
        
        brain_stats = self.brain.get_stats()
        accuracy = self.brain.get_prediction_accuracy(30)
        msg_lower = message.lower()
        
        if any(w in msg_lower for w in ["accuracy", "performance", "how well"]):
            response = self._format_performance(accuracy, brain_stats)
        elif any(w in msg_lower for w in ["brain", "learning", "knowledge"]):
            response = self._format_brain(brain_stats)
        elif any(w in msg_lower for w in ["analyze", "signal", "buy", "sell"]):
            symbol = self._extract_symbol(message)
            if symbol:
                analysis = await self.analyze_stock(symbol)
                response = self._format_analysis(analysis) if "error" not in analysis else f"Couldn't analyze {symbol}: {analysis.get('error', '')}"
            else:
                response = "Which stock? Try: RELIANCE, TCS, HDFCBANK, INFY."
        else:
            if self.status == "ready":
                prompt = f'You are ARTH, an AI trading assistant for Indian stock markets. The user asked: "{message}". Your stats: {brain_stats["total_predictions"]} predictions, {brain_stats["overall_accuracy"]}% accuracy. Respond concisely.'
                ai_resp = await self.router.analyze(prompt, temperature=0.7)
                response = ai_resp.get("response", str(ai_resp)) if ai_resp else self._fallback(message, brain_stats)
            else:
                response = self._fallback(message, brain_stats)
        
        return {"response": response, "timestamp": datetime.now(timezone.utc).isoformat(), "arth_status": self.status}
    
    async def get_probability(self, symbol: str) -> Dict:
        analysis = await self.analyze_stock(symbol)
        return analysis if "error" in analysis else analysis.get("probability", {})
    
    async def self_reflect(self, days: int = 7) -> Dict:
        accuracy = self.brain.get_prediction_accuracy(days)
        brain_stats = self.brain.get_stats()
        signals_by_type = self.brain.get_signals_by_accuracy(days)
        
        best = max(signals_by_type.items(), key=lambda x: x[1].get("accuracy", 0)) if signals_by_type else ("N/A", {"accuracy": 0})
        worst = min(signals_by_type.items(), key=lambda x: x[1].get("accuracy", 0)) if signals_by_type else ("N/A", {"accuracy": 0})
        
        if accuracy["total_predictions"] >= 10:
            self._generate_learning_rules(signals_by_type)
        
        return {
            "period_days": days, "accuracy": accuracy, "brain_stats": brain_stats,
            "signals_breakdown": signals_by_type,
            "best_signal": {"type": best[0], **best[1]},
            "worst_signal": {"type": worst[0], **worst[1]},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    async def _resolve_pending_predictions(self):
        """Resolve old predictions against actual prices."""
        try:
            unresolved = self.brain.get_unresolved_predictions(days_old=1)
            resolved = 0
            for pred in unresolved:
                stock = await price_fetcher.get_price(pred["symbol"])
                if not stock or not pred.get("entry_price"):
                    continue
                
                entry = pred["entry_price"]
                if pred["signal"] == "BUY":
                    ret = (stock.current_price - entry) / entry * 100
                elif pred["signal"] == "SELL":
                    ret = (entry - stock.current_price) / entry * 100
                else:
                    ret = 0
                
                outcome = "WIN" if ret > 0.5 else "LOSS" if ret < -0.5 else "NEUTRAL"
                self.brain.resolve_prediction(pred["id"], outcome, round(ret, 2))
                resolved += 1
            
            if resolved:
                logger.info(f"ARTH: Resolved {resolved} predictions")
        except Exception as e:
            logger.error(f"Error resolving predictions: {e}")
    
    def _generate_learning_rules(self, signals_by_type: Dict):
        for sig_type, data in signals_by_type.items():
            if data["total"] >= 5:
                if data["accuracy"] >= 70:
                    self.brain.store_learning_rule(f"boost_{sig_type}", "confidence_adjustment", {"signal": sig_type, "adjustment": 5}, data["accuracy"] / 100)
                elif data["accuracy"] <= 40:
                    self.brain.store_learning_rule(f"reduce_{sig_type}", "confidence_adjustment", {"signal": sig_type, "adjustment": -5}, (100 - data["accuracy"]) / 100)
    
    def _extract_symbol(self, message: str) -> Optional[str]:
        from models.stock import NIFTY_50_SYMBOLS
        for symbol in NIFTY_50_SYMBOLS:
            if symbol in message.upper():
                return symbol
        return None
    
    def _format_performance(self, acc, stats) -> str:
        return (f"Performance: {stats['total_predictions']} predictions, "
                f"{stats['overall_accuracy']}% accuracy. "
                f"Last {acc['period_days']}d: {acc['accuracy']}% ({acc['correct_predictions']}/{acc['total_predictions']}).")
    
    def _format_brain(self, stats) -> str:
        return (f"Brain: {stats['total_predictions']} predictions, "
                f"{stats['total_patterns']} patterns, {stats['active_rules']} rules, "
                f"{stats['overall_accuracy']}% accuracy.")
    
    def _format_analysis(self, a) -> str:
        s = a["signal"]
        e = "🟢" if s == "BUY" else "🔴" if s == "SELL" else "🟡"
        r = f"{e} {a['symbol']}: {s} ({a['confidence']}%) at ₹{a['price']['current']:.2f}"
        if a.get("levels", {}).get("entry"):
            r += f"\nEntry: ₹{a['levels']['entry']:.0f} | Target: ₹{a['levels']['target']:.0f} | Stop: ₹{a['levels']['stop_loss']:.0f}"
        p = a.get("probability", {})
        if p:
            r += f"\nWin Prob: {p.get('win_probability', '?')}% | Position: {p.get('position_size', '?')}"
        return r
    
    def _fallback(self, msg, stats) -> str:
        return f"I'm ARTH. Ask me to analyze stocks (e.g., 'Analyze RELIANCE'), check performance, or explain my brain. Tracking {stats['total_predictions']} predictions."
    
    def get_provider_status(self) -> List[Dict]:
        return self.router.get_status() if self.router else []


# Singleton
arth = ArthAgent()
