"""
ARTH - AI Trading Agent
The central AI agent that orchestrates all trading intelligence
"""

import logging
from datetime import datetime
from typing import Dict, Optional, Any, List

from ai_agent.brain import ArthBrain
from ai_agent.router import AIRouter
from ai_agent.analyzer import ArthAnalyzer
from ai_agent.prompts import (
    SIGNAL_ANALYSIS_PROMPT, MARKET_SENTIMENT_PROMPT,
    SELF_REFLECTION_PROMPT, PROBABILITY_CALCULATION_PROMPT
)
from services.price_fetcher import price_fetcher
from services.indicators import indicators
from services.signal_generator import signal_generator
from models.stock import SignalType

logger = logging.getLogger(__name__)


class ArthAgent:
    """
    ARTH - The AI Trading Agent
    Orchestrates analysis, learning, and signal generation
    """
    
    def __init__(self):
        self.brain: Optional[ArthBrain] = None
        self.router: Optional[AIRouter] = None
        self.analyzer: Optional[ArthAnalyzer] = None
        self.status = "initializing"
        self._initialized = False
    
    async def initialize(self):
        """Initialize ARTH and all components"""
        try:
            logger.info("ARTH: Initializing brain...")
            self.brain = ArthBrain()
            
            logger.info("ARTH: Initializing AI router...")
            self.router = AIRouter()
            
            logger.info("ARTH: Initializing analyzer...")
            self.analyzer = ArthAnalyzer()
            
            available = self.router.get_available_providers()
            if available:
                self.status = "ready"
                logger.info(f"ARTH: Ready! AI providers: {available}")
            else:
                self.status = "rule-based"
                logger.info("ARTH: No AI providers available - running in rule-based mode")
            
            self._initialized = True
            
            # Resolve any pending predictions
            await self._resolve_pending_predictions()
            
        except Exception as e:
            logger.error(f"ARTH initialization error: {e}")
            self.status = "error"
    
    async def shutdown(self):
        """Clean shutdown"""
        if self.brain:
            self.brain.close()
        logger.info("ARTH: Shutdown complete")
    
    async def analyze_stock(self, symbol: str) -> Dict[str, Any]:
        """
        Full ARTH analysis of a stock - combines rule-based + AI
        """
        if not self._initialized:
            return {"error": "ARTH not initialized"}
        
        # 1. Get stock data
        stock = await price_fetcher.get_price(symbol)
        if not stock:
            return {"error": f"Could not fetch data for {symbol}"}
        
        # 2. Get historical data for indicators
        df = await price_fetcher.get_historical_data(symbol)
        if df is None or df.empty:
            return {"error": f"No historical data for {symbol}"}
        
        # 3. Calculate technical indicators
        ind = indicators.calculate_all(df)
        
        # 4. Generate rule-based signal
        rule_signal = await signal_generator.generate_signal(symbol)
        
        # 5. Detect chart patterns
        patterns = self.analyzer.detect_patterns(df)
        
        # 6. Get AI analysis if available
        ai_result = None
        if self.status == "ready":
            # Build prompt with context
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
        
        # 7. Combine rule-based and AI analysis
        if rule_signal:
            enhanced = self.analyzer.enhance_signal_with_ai(
                stock, ind, rule_signal.signal, rule_signal.confidence, ai_result
            )
        else:
            enhanced = {
                "signal": "HOLD",
                "confidence": 50,
                "source": "fallback",
                "ai_enhanced": False
            }
        
        # 8. Calculate probability
        probability = self.analyzer.calculate_probability(
            symbol, enhanced['signal'], enhanced['confidence'], ind, stock
        )
        
        # 9. Store prediction in ARTH's brain
        prediction_id = self.brain.store_prediction(
            symbol=symbol,
            signal=enhanced['signal'],
            confidence=enhanced['confidence'],
            entry_price=enhanced.get('ai_entry') or (rule_signal.entry_price if rule_signal else None),
            target_price=enhanced.get('ai_target') or (rule_signal.target_price if rule_signal else None),
            stop_loss=enhanced.get('ai_stop_loss') or (rule_signal.stop_loss if rule_signal else None),
            indicators={
                "rsi": ind.rsi,
                "sma_20": ind.sma_20,
                "sma_50": ind.sma_50,
                "macd": ind.macd,
                "volume_ratio": ind.volume_ratio,
            },
            ai_provider=enhanced.get('ai_provider'),
            ai_reasoning=enhanced.get('ai_reasoning'),
            pattern_used=patterns[0]['name'] if patterns else None,
        )
        
        # 10. Build complete response
        result = {
            "symbol": symbol,
            "company_name": stock.name,
            "timestamp": datetime.utcnow().isoformat(),
            "price": {
                "current": stock.current_price,
                "change": stock.change,
                "change_percent": stock.change_percent,
                "open": stock.open,
                "high": stock.high,
                "low": stock.low,
                "volume": stock.volume,
            },
            "indicators": {
                "rsi": ind.rsi,
                "sma_20": ind.sma_20,
                "sma_50": ind.sma_50,
                "sma_200": ind.sma_200,
                "macd": ind.macd,
                "macd_signal": ind.macd_signal,
                "macd_histogram": ind.macd_histogram,
                "support": ind.support,
                "resistance": ind.resistance,
                "volume_ratio": ind.volume_ratio,
            },
            "signal": enhanced['signal'],
            "confidence": enhanced['confidence'],
            "source": enhanced['source'],
            "ai_enhanced": enhanced['ai_enhanced'],
            "ai_provider": enhanced.get('ai_provider'),
            "ai_reasoning": enhanced.get('ai_reasoning', ''),
            "probability": probability,
            "levels": {
                "entry": enhanced.get('ai_entry') or (rule_signal.entry_price if rule_signal else None),
                "target": enhanced.get('ai_target') or (rule_signal.target_price if rule_signal else None),
                "stop_loss": enhanced.get('ai_stop_loss') or (rule_signal.stop_loss if rule_signal else None),
                "risk_reward": rule_signal.risk_reward if rule_signal else None,
            },
            "patterns": patterns,
            "key_factors": enhanced.get('key_factors', []),
            "risks": enhanced.get('risks', []),
            "timeframe": enhanced.get('timeframe', 'MEDIUM'),
            "prediction_id": prediction_id,
            "arth_status": self.status,
            "brain_stats": self.brain.get_stats(),
        }
        
        return result
    
    async def chat(self, message: str, context: Dict = None) -> Dict:
        """Chat with ARTH about markets/trading"""
        if not self._initialized:
            return {"response": "ARTH is still initializing. Please wait a moment."}
        
        # Build context
        brain_stats = self.brain.get_stats()
        accuracy = self.brain.get_prediction_accuracy(30)
        
        # Try to understand intent
        msg_lower = message.lower()
        
        if any(w in msg_lower for w in ["accuracy", "performance", "how well", "track record"]):
            response = self._format_performance_response(accuracy, brain_stats)
        elif any(w in msg_lower for w in ["brain", "learning", "knowledge"]):
            response = self._format_brain_response(brain_stats)
        elif any(w in msg_lower for w in ["analyze", "signal", "buy", "sell"]):
            # Extract symbol
            symbol = self._extract_symbol(message)
            if symbol:
                analysis = await self.analyze_stock(symbol)
                if "error" not in analysis:
                    response = self._format_analysis_response(analysis)
                else:
                    response = f"Sorry, I couldn't analyze {symbol}. {analysis.get('error', '')}"
            else:
                response = "Which stock would you like me to analyze? Please provide a symbol like RELIANCE, TCS, or HDFCBANK."
        else:
            # Use AI for general conversation
            if self.status == "ready":
                prompt = f"""You are ARTH, an AI trading assistant for Indian stock markets. 
                The user asked: "{message}"
                
                Your current stats:
                - Predictions made: {brain_stats['total_predictions']}
                - Overall accuracy: {brain_stats['overall_accuracy']}%
                - Active rules: {brain_stats['active_rules']}
                - Patterns learned: {brain_stats['total_patterns']}
                
                Respond helpfully and concisely. If asked about stocks, offer to analyze them."""
                
                ai_response = await self.router.analyze(prompt, temperature=0.7)
                if ai_response:
                    response = ai_response.get("response", ai_response.get("raw_response", str(ai_response)))
                else:
                    response = self._get_fallback_response(message, brain_stats)
            else:
                response = self._get_fallback_response(message, brain_stats)
        
        return {
            "response": response,
            "timestamp": datetime.utcnow().isoformat(),
            "arth_status": self.status,
        }
    
    async def get_probability(self, symbol: str) -> Dict:
        """Get trade probability for a symbol"""
        analysis = await self.analyze_stock(symbol)
        if "error" in analysis:
            return analysis
        return analysis.get("probability", {})
    
    async def self_reflect(self, days: int = 7) -> Dict:
        """ARTH self-reflection and learning"""
        accuracy = self.brain.get_prediction_accuracy(days)
        brain_stats = self.brain.get_stats()
        signals_by_type = self.brain.get_signals_by_accuracy(days)
        active_rules = self.brain.get_active_rules()
        
        # Find best and worst signals
        best_signal = max(signals_by_type.items(), key=lambda x: x[1].get('accuracy', 0)) if signals_by_type else ("N/A", {"accuracy": 0})
        worst_signal = min(signals_by_type.items(), key=lambda x: x[1].get('accuracy', 0)) if signals_by_type else ("N/A", {"accuracy": 0})
        
        if self.status == "ready" and accuracy['total_predictions'] > 5:
            prompt = SELF_REFLECTION_PROMPT.format(
                days=days,
                total_predictions=accuracy['total_predictions'],
                accuracy=accuracy['accuracy'],
                best_signal=f"{best_signal[0]} ({best_signal[1]['accuracy']}%)",
                worst_signal=f"{worst_signal[0]} ({worst_signal[1]['accuracy']}%)",
                active_rules=len(active_rules),
                recent_failures="See database"
            )
            
            ai_insight = await self.router.analyze(prompt, temperature=0.5)
        else:
            ai_insight = None
        
        # Generate learning rules from performance
        if accuracy['total_predictions'] >= 10:
            self._generate_learning_rules(signals_by_type, accuracy)
        
        return {
            "period_days": days,
            "accuracy": accuracy,
            "brain_stats": brain_stats,
            "signals_breakdown": signals_by_type,
            "best_signal": {"type": best_signal[0], **best_signal[1]},
            "worst_signal": {"type": worst_signal[0], **worst_signal[1]},
            "ai_insight": ai_insight,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    async def _resolve_pending_predictions(self):
        """Check and resolve old predictions against actual prices"""
        try:
            unresolved = self.brain.get_unresolved_predictions(days_old=1)
            resolved_count = 0
            
            for pred in unresolved:
                try:
                    # Get current price
                    stock = await price_fetcher.get_price(pred['symbol'])
                    if not stock:
                        continue
                    
                    entry_price = pred['entry_price']
                    if not entry_price:
                        continue
                    
                    # Calculate actual return
                    if pred['signal'] == 'BUY':
                        actual_return = (stock.current_price - entry_price) / entry_price * 100
                    elif pred['signal'] == 'SELL':
                        actual_return = (entry_price - stock.current_price) / entry_price * 100
                    else:
                        actual_return = 0
                    
                    # Determine outcome
                    if actual_return > 0.5:
                        outcome = "WIN"
                    elif actual_return < -0.5:
                        outcome = "LOSS"
                    else:
                        outcome = "NEUTRAL"
                    
                    self.brain.resolve_prediction(pred['id'], outcome, round(actual_return, 2))
                    resolved_count += 1
                    
                except Exception as e:
                    logger.error(f"Error resolving prediction {pred['id']}: {e}")
            
            if resolved_count > 0:
                logger.info(f"ARTH: Resolved {resolved_count} pending predictions")
        
        except Exception as e:
            logger.error(f"Error resolving predictions: {e}")
    
    def _generate_learning_rules(self, signals_by_type: Dict, accuracy: Dict):
        """Generate new learning rules based on performance analysis"""
        for signal_type, data in signals_by_type.items():
            if data['total'] >= 5:
                if data['accuracy'] >= 70:
                    self.brain.store_learning_rule(
                        name=f"boost_{signal_type}_confidence",
                        rule_type="confidence_adjustment",
                        rule_data={"signal": signal_type, "adjustment": +5},
                        weight=data['accuracy'] / 100
                    )
                elif data['accuracy'] <= 40:
                    self.brain.store_learning_rule(
                        name=f"reduce_{signal_type}_confidence",
                        rule_type="confidence_adjustment",
                        rule_data={"signal": signal_type, "adjustment": -5},
                        weight=(100 - data['accuracy']) / 100
                    )
    
    def _extract_symbol(self, message: str) -> Optional[str]:
        """Try to extract stock symbol from message"""
        from models.stock import NIFTY_50_SYMBOLS
        msg_upper = message.upper()
        for symbol in NIFTY_50_SYMBOLS:
            if symbol in msg_upper:
                return symbol
        return None
    
    def _format_performance_response(self, accuracy: Dict, stats: Dict) -> str:
        return (
            f"Here's my performance report:\n"
            f"- Total predictions: {stats['total_predictions']}\n"
            f"- Resolved: {stats['resolved_predictions']}\n"
            f"- Overall accuracy: {stats['overall_accuracy']}%\n"
            f"- Last {accuracy['period_days']} days: {accuracy['accuracy']}% accuracy "
            f"({accuracy['correct_predictions']}/{accuracy['total_predictions']} correct)\n"
            f"- Patterns learned: {stats['total_patterns']}\n"
            f"- Active rules: {stats['active_rules']}"
        )
    
    def _format_brain_response(self, stats: Dict) -> str:
        return (
            f"My brain currently holds:\n"
            f"- {stats['total_predictions']} total predictions stored\n"
            f"- {stats['resolved_predictions']} predictions resolved with outcomes\n"
            f"- {stats['total_patterns']} trading patterns learned\n"
            f"- {stats['active_rules']} active trading rules\n"
            f"- Overall accuracy: {stats['overall_accuracy']}%\n\n"
            f"I learn from every prediction and improve my signals over time!"
        )
    
    def _format_analysis_response(self, analysis: Dict) -> str:
        signal = analysis['signal']
        confidence = analysis['confidence']
        emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "🟡"
        
        response = f"{emoji} {analysis['symbol']} ({analysis['company_name']}):\n"
        response += f"Signal: {signal} | Confidence: {confidence}%\n"
        response += f"Price: ₹{analysis['price']['current']:.2f} ({analysis['price']['change_percent']:.2f}%)\n"
        
        if analysis.get('levels', {}).get('entry'):
            response += f"Entry: ₹{analysis['levels']['entry']:.2f}\n"
            response += f"Target: ₹{analysis['levels']['target']:.2f}\n"
            response += f"Stop Loss: ₹{analysis['levels']['stop_loss']:.2f}\n"
        
        prob = analysis.get('probability', {})
        if prob:
            response += f"Win Probability: {prob.get('win_probability', 'N/A')}%\n"
            response += f"Position Size: {prob.get('position_size', 'N/A')}\n"
        
        if analysis.get('ai_reasoning'):
            response += f"\nARTH's Analysis: {analysis['ai_reasoning'][:200]}"
        
        return response
    
    def _get_fallback_response(self, message: str, stats: Dict) -> str:
        return (
            f"I'm ARTH, your AI trading assistant. I can:\n"
            f"- Analyze stocks (e.g., 'Analyze RELIANCE')\n"
            f"- Check my performance (e.g., 'How accurate am I?')\n"
            f"- Explain my brain (e.g., 'What have you learned?')\n\n"
            f"Currently tracking {stats['total_predictions']} predictions "
            f"with {stats['overall_accuracy']}% accuracy."
        )
    
    def get_provider_status(self) -> List[Dict]:
        """Get status of all AI providers"""
        if self.router:
            return self.router.get_status()
        return []


# Singleton
arth = ArthAgent()
