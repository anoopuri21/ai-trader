"""
ARTH's Self-Learning Scheduler
Periodically resolves predictions, reflects, and improves
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from ai_agent.arth import arth
from services.price_fetcher import price_fetcher
from models.stock import NIFTY_50_SYMBOLS

logger = logging.getLogger(__name__)


class LearningScheduler:
    """Manages ARTH's periodic self-improvement tasks"""
    
    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the learning scheduler"""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("ARTH Learning Scheduler started")
    
    async def stop(self):
        """Stop the learning scheduler"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("ARTH Learning Scheduler stopped")
    
    async def _run_loop(self):
        """Main learning loop"""
        while self._running:
            try:
                # Every 30 minutes: resolve pending predictions
                await self._resolve_predictions()
                
                # Every 2 hours: self-reflect and learn
                await self._self_reflect()
                
                # Every 6 hours: run quick backtests on top stocks
                await self._run_quick_backtests()
                
                # Wait 30 minutes before next cycle
                await asyncio.sleep(1800)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Learning scheduler error: {e}")
                await asyncio.sleep(300)  # Wait 5 min on error
    
    async def _resolve_predictions(self):
        """Resolve pending predictions against actual prices"""
        if not arth.brain:
            return
        
        try:
            unresolved = arth.brain.get_unresolved_predictions(days_old=0)
            resolved = 0
            
            for pred in unresolved:
                try:
                    stock = await price_fetcher.get_price(pred['symbol'])
                    if not stock or not pred.get('entry_price'):
                        continue
                    
                    entry = pred['entry_price']
                    if pred['signal'] == 'BUY':
                        actual_return = (stock.current_price - entry) / entry * 100
                    elif pred['signal'] == 'SELL':
                        actual_return = (entry - stock.current_price) / entry * 100
                    else:
                        actual_return = 0
                    
                    if actual_return > 0.5:
                        outcome = "WIN"
                    elif actual_return < -0.5:
                        outcome = "LOSS"
                    else:
                        outcome = "NEUTRAL"
                    
                    arth.brain.resolve_prediction(pred['id'], outcome, round(actual_return, 2))
                    resolved += 1
                    
                    # Update any active learning rules
                    if pred.get('pattern_used'):
                        arth.brain._update_pattern_success(
                            pred['pattern_used'], 
                            1 if outcome == "WIN" else 0
                        )
                    
                except Exception as e:
                    logger.debug(f"Could not resolve prediction {pred['id']}: {e}")
            
            if resolved > 0:
                logger.info(f"ARTH: Resolved {resolved} predictions")
        
        except Exception as e:
            logger.error(f"Error resolving predictions: {e}")
    
    async def _self_reflect(self):
        """Run self-reflection to improve rules"""
        if not arth.brain:
            return
        
        try:
            stats = arth.brain.get_stats()
            if stats['resolved_predictions'] < 5:
                return  # Not enough data to reflect
            
            accuracy = arth.brain.get_prediction_accuracy(7)
            signals = arth.brain.get_signals_by_accuracy(7)
            
            # Generate/update rules based on performance
            for signal_type, data in signals.items():
                if data['total'] >= 3:
                    if data['accuracy'] >= 70:
                        arth.brain.store_learning_rule(
                            f"boost_{signal_type}",
                            "confidence_adjustment",
                            {"signal": signal_type, "adjustment": 5},
                            weight=data['accuracy'] / 100
                        )
                    elif data['accuracy'] <= 35:
                        arth.brain.store_learning_rule(
                            f"reduce_{signal_type}",
                            "confidence_adjustment",
                            {"signal": signal_type, "adjustment": -5},
                            weight=(100 - data['accuracy']) / 100
                        )
            
            logger.info(f"ARTH: Self-reflection complete. Accuracy: {accuracy['accuracy']}%")
        
        except Exception as e:
            logger.error(f"Error in self-reflection: {e}")
    
    async def _run_quick_backtests(self):
        """Run quick backtests on top 5 Nifty stocks"""
        if not arth.brain:
            return
        
        try:
            from ai_agent.backtest import backtest_engine
            
            # Pick top 5 liquid stocks
            top_stocks = ["RELIANCE", "HDFCBANK", "INFY", "TCS", "ICICIBANK"]
            
            for symbol in top_stocks:
                try:
                    await backtest_engine.run_backtest(
                        symbol=symbol,
                        strategy="combined",
                        initial_capital=100000
                    )
                    await asyncio.sleep(1)  # Rate limit
                except Exception as e:
                    logger.debug(f"Quick backtest failed for {symbol}: {e}")
            
            logger.info("ARTH: Quick backtests complete")
        
        except Exception as e:
            logger.error(f"Error in quick backtests: {e}")


# Singleton
scheduler = LearningScheduler()
