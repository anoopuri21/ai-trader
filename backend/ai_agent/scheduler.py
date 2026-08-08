"""
ARTH's Self-Learning Scheduler

Architecture Fix: Scheduler now starts in a delayed background task
so it doesn't block the server from accepting requests during startup.
"""

import logging
import asyncio
from typing import Optional

from ai_agent.arth import arth
from services.price_fetcher import price_fetcher

logger = logging.getLogger(__name__)


class LearningScheduler:
    """Manages ARTH's periodic self-improvement tasks."""
    
    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        if self._running:
            return
        self._running = True
        # Delay start by 10s so server can accept requests first
        self._task = asyncio.create_task(self._delayed_start())
        logger.info("Learning Scheduler scheduled (10s delay)")
    
    async def _delayed_start(self):
        await asyncio.sleep(10)
        logger.info("Learning Scheduler running...")
        await self._run_loop()
    
    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Learning Scheduler stopped")
    
    async def _run_loop(self):
        while self._running:
            try:
                await self._resolve_predictions()
                await self._self_reflect()
                await self._run_quick_backtests()
                await asyncio.sleep(1800)  # 30 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(300)
    
    async def _resolve_predictions(self):
        if not arth.brain:
            return
        try:
            unresolved = arth.brain.get_unresolved_predictions(days_old=0)
            resolved = 0
            for pred in unresolved:
                try:
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
                    arth.brain.resolve_prediction(pred["id"], outcome, round(ret, 2))
                    resolved += 1
                except Exception:
                    pass
            if resolved:
                logger.info(f"Scheduler: Resolved {resolved} predictions")
        except Exception as e:
            logger.error(f"Resolve error: {e}")
    
    async def _self_reflect(self):
        if not arth.brain:
            return
        try:
            stats = arth.brain.get_stats()
            if stats["resolved_predictions"] < 5:
                return
            signals = arth.brain.get_signals_by_accuracy(7)
            for sig_type, data in signals.items():
                if data["total"] >= 3:
                    if data["accuracy"] >= 70:
                        arth.brain.store_learning_rule(f"boost_{sig_type}", "confidence_adjustment", {"signal": sig_type, "adjustment": 5}, data["accuracy"] / 100)
                    elif data["accuracy"] <= 35:
                        arth.brain.store_learning_rule(f"reduce_{sig_type}", "confidence_adjustment", {"signal": sig_type, "adjustment": -5}, (100 - data["accuracy"]) / 100)
        except Exception as e:
            logger.error(f"Self-reflect error: {e}")
    
    async def _run_quick_backtests(self):
        if not arth.brain:
            return
        try:
            from ai_agent.backtest import backtest_engine
            for symbol in ["RELIANCE", "HDFCBANK", "INFY"]:
                try:
                    await backtest_engine.run_backtest(symbol=symbol, strategy="combined")
                    await asyncio.sleep(1)
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Quick backtest error: {e}")


scheduler = LearningScheduler()
