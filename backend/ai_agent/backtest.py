"""
ARTH's Backtesting Engine

Trading Logic Fixes:
  1. Transaction costs included (slippage + STT + brokerage)
  2. RSI uses same Wilder smoothing as live indicator service
  3. Stop-loss uses ATR-based levels (matching live strategy)
  4. Results stored via centralized database
  
Architecture Fix: Uses centralized DatabaseManager via ArthBrain.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np

from config import settings
from services.price_fetcher import price_fetcher
from ai_agent.brain import ArthBrain

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Backtesting engine with realistic transaction costs."""
    
    def __init__(self):
        self.brain = ArthBrain()
        # Transaction costs from settings
        self.slippage = settings.slippage_pct
        self.stt = settings.stt_pct
        self.brokerage = settings.brokerage_pct
        self.total_cost = self.slippage + self.stt + self.brokerage  # ~0.17% per trade
    
    async def run_backtest(
        self, symbol: str, strategy: str = "rule_based",
        start_date: str = None, end_date: str = None,
        initial_capital: float = 100000.0, position_size_pct: float = 0.1,
    ) -> Dict[str, Any]:
        if not start_date:
            start_date = (datetime.utcnow() - timedelta(days=365)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.utcnow().strftime("%Y-%m-%d")
        
        df = await price_fetcher.get_historical_data(symbol, period="1y", interval="1d")
        if df is None or df.empty:
            return {"error": f"No data available for {symbol}"}
        
        strategies = {
            "rule_based": self._backtest_rule_based,
            "momentum": self._backtest_momentum,
            "mean_reversion": self._backtest_mean_reversion,
            "combined": self._backtest_combined,
        }
        
        func = strategies.get(strategy, self._backtest_rule_based)
        trades = func(df, symbol, position_size_pct)
        metrics = self._calculate_metrics(trades, initial_capital)
        
        # Store in centralized DB
        try:
            self.brain.db.store_backtest_result(
                f"{symbol}_{strategy}", symbol, start_date, end_date, metrics
            )
            # Store winning patterns
            for trade in trades:
                if trade["pnl_percent"] > 0:
                    self.brain.store_pattern(
                        f"{trade['type']}_{trade['exit_reason']}_{symbol}",
                        trade["type"], {"pnl": trade["pnl_percent"], "strategy": strategy},
                    )
        except Exception as e:
            logger.error(f"Error storing backtest: {e}")
        
        logger.info(f"Backtest: {symbol} {strategy} — {metrics['total_trades']} trades, {metrics['win_rate']}% win rate, {metrics['total_return']}% return")
        
        return {
            "symbol": symbol, "strategy": strategy,
            "period": {"start": start_date, "end": end_date},
            "metrics": metrics, "trades": trades[-20:],
            "total_trades": len(trades),
            "transaction_cost_pct": round(self.total_cost * 100, 3),
        }
    
    def _backtest_rule_based(self, df: pd.DataFrame, symbol: str, position_pct: float) -> List[Dict]:
        """Rule-based: SMA crossover + RSI + MACD + Bollinger + ATR stops."""
        trades = []
        position = None
        
        df = df.copy()
        df["sma_20"] = df["Close"].rolling(20).mean()
        df["sma_50"] = df["Close"].rolling(50).mean()
        df["rsi"] = self._calc_rsi(df["Close"])  # Wilder smoothing — matches live
        df["macd"] = df["Close"].ewm(span=12, adjust=False).mean() - df["Close"].ewm(span=26, adjust=False).mean()
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]
        df["bb_mid"] = df["Close"].rolling(20).mean()
        df["bb_std"] = df["Close"].rolling(20).std()
        df["bb_upper"] = df["bb_mid"] + 2 * df["bb_std"]
        df["bb_lower"] = df["bb_mid"] - 2 * df["bb_std"]
        
        # ATR for stops
        df["atr"] = self._calc_atr(df)
        
        for i in range(200, len(df)):
            row = df.iloc[i]
            price = row["Close"]
            
            if pd.isna(row["sma_20"]) or pd.isna(row["sma_50"]) or pd.isna(row["rsi"]):
                continue
            
            # ── EXIT LOGIC ──
            if position:
                exit_reason = None
                exit_price = price
                
                if position["type"] == "long":
                    if price <= position["stop_loss"]:
                        exit_reason = "stop_loss"
                    elif price >= position["target"]:
                        exit_reason = "take_profit"
                    elif row["macd_hist"] < 0 and df.iloc[i-1]["macd_hist"] >= 0:
                        exit_reason = "macd_bearish_cross"
                else:
                    if price >= position["stop_loss"]:
                        exit_reason = "stop_loss"
                    elif price <= position["target"]:
                        exit_reason = "take_profit"
                    elif row["macd_hist"] > 0 and df.iloc[i-1]["macd_hist"] <= 0:
                        exit_reason = "macd_bullish_cross"
                
                if exit_reason:
                    if position["type"] == "long":
                        pnl_pct = (exit_price - position["entry"]) / position["entry"] * 100
                    else:
                        pnl_pct = (position["entry"] - exit_price) / position["entry"] * 100
                    
                    # TRADING FIX: Deduct transaction costs (round trip)
                    pnl_pct -= self.total_cost * 100 * 2  # Entry + exit
                    
                    trades.append({
                        "symbol": symbol, "type": position["type"],
                        "entry_price": round(position["entry"], 2),
                        "exit_price": round(exit_price, 2),
                        "entry_date": str(position["date"]),
                        "exit_date": str(row.name),
                        "pnl_percent": round(pnl_pct, 2),
                        "exit_reason": exit_reason,
                        "holding_days": (row.name - position["date"]).days if hasattr(row.name, "isoformat") else 0,
                    })
                    position = None
            
            # ── ENTRY LOGIC ──
            if not position:
                buy_score = 0
                sell_score = 0
                
                if row["sma_20"] > row["sma_50"]:
                    buy_score += 1
                else:
                    sell_score += 1
                
                if price > row["sma_20"]:
                    buy_score += 1
                elif price < row["sma_20"]:
                    sell_score += 1
                
                # Contextual RSI (matching live logic)
                if row["sma_20"] > row["sma_50"]:  # Bullish trend
                    if row["rsi"] < 30:
                        buy_score += 2
                    elif 40 <= row["rsi"] <= 70:
                        buy_score += 1
                    elif row["rsi"] > 80:
                        sell_score += 1
                else:  # Bearish trend
                    if row["rsi"] > 70:
                        sell_score += 2
                    elif 30 <= row["rsi"] <= 50:
                        sell_score += 1
                    elif row["rsi"] < 20:
                        buy_score += 1
                
                if row["macd"] > row["macd_signal"]:
                    buy_score += 1
                else:
                    sell_score += 1
                
                if not pd.isna(row["bb_lower"]) and price < row["bb_lower"]:
                    buy_score += 2
                elif not pd.isna(row["bb_upper"]) and price > row["bb_upper"]:
                    sell_score += 2
                
                avg_vol = df["Volume"].iloc[max(0, i-20):i].mean()
                if row["Volume"] > avg_vol * 1.5:
                    if buy_score > sell_score:
                        buy_score += 1
                    elif sell_score > buy_score:
                        sell_score += 1
                
                # ATR-based stops/targets (matching live)
                atr = row["atr"] if not pd.isna(row["atr"]) else price * 0.02
                
                if buy_score >= 4 and buy_score > sell_score + 1:
                    stop_dist = atr * settings.atr_stop_multiplier
                    target_dist = atr * settings.atr_target_multiplier
                    stop_pct = max(0.01, min(0.05, stop_dist / price))
                    target_pct = max(0.02, min(0.10, target_dist / price))
                    position = {
                        "type": "long", "entry": price, "date": row.name,
                        "stop_loss": price * (1 - stop_pct),
                        "target": price * (1 + target_pct),
                    }
                elif sell_score >= 4 and sell_score > buy_score + 1:
                    stop_dist = atr * settings.atr_stop_multiplier
                    target_dist = atr * settings.atr_target_multiplier
                    stop_pct = max(0.01, min(0.05, stop_dist / price))
                    target_pct = max(0.02, min(0.10, target_dist / price))
                    position = {
                        "type": "short", "entry": price, "date": row.name,
                        "stop_loss": price * (1 + stop_pct),
                        "target": price * (1 - target_pct),
                    }
        
        return trades
    
    def _backtest_momentum(self, df: pd.DataFrame, symbol: str, position_pct: float) -> List[Dict]:
        """Momentum: RSI + Volume + ROC."""
        trades = []
        position = None
        
        df = df.copy()
        df["rsi"] = self._calc_rsi(df["Close"])
        df["vol_ma"] = df["Volume"].rolling(20).mean()
        df["roc"] = df["Close"].pct_change(10, fill_method=None) * 100
        df["atr"] = self._calc_atr(df)
        
        for i in range(25, len(df)):
            row = df.iloc[i]
            price = row["Close"]
            if pd.isna(row["rsi"]) or pd.isna(row["roc"]):
                continue
            
            if position:
                pnl_pct = ((price - position["entry"]) / position["entry"] * 100) if position["type"] == "long" else ((position["entry"] - price) / position["entry"] * 100)
                
                if (position["type"] == "long" and row["rsi"] > 70) or (position["type"] == "short" and row["rsi"] < 30):
                    pnl_pct -= self.total_cost * 200
                    trades.append({**self._make_trade(symbol, position, price, row, pnl_pct, "rsi_exit")})
                    position = None
                elif (position["type"] == "long" and price < position["entry"] * 0.97) or (position["type"] == "short" and price > position["entry"] * 1.03):
                    pnl_pct -= self.total_cost * 200
                    trades.append({**self._make_trade(symbol, position, price, row, pnl_pct, "stop_loss")})
                    position = None
            
            if not position:
                if row["rsi"] < 30 and row["roc"] > 0 and row["Volume"] > row["vol_ma"]:
                    position = {"type": "long", "entry": price, "date": row.name}
                elif row["rsi"] > 70 and row["roc"] < 0 and row["Volume"] > row["vol_ma"]:
                    position = {"type": "short", "entry": price, "date": row.name}
        
        return trades
    
    def _backtest_mean_reversion(self, df: pd.DataFrame, symbol: str, position_pct: float) -> List[Dict]:
        """Mean reversion: Bollinger Bands."""
        trades = []
        position = None
        
        df = df.copy()
        df["bb_mid"] = df["Close"].rolling(20).mean()
        df["bb_std"] = df["Close"].rolling(20).std()
        df["bb_upper"] = df["bb_mid"] + 2 * df["bb_std"]
        df["bb_lower"] = df["bb_mid"] - 2 * df["bb_std"]
        
        for i in range(25, len(df)):
            row = df.iloc[i]
            price = row["Close"]
            if pd.isna(row["bb_mid"]):
                continue
            
            if position:
                pnl_pct = ((price - position["entry"]) / position["entry"] * 100) if position["type"] == "long" else ((position["entry"] - price) / position["entry"] * 100)
                
                if (position["type"] == "long" and price >= row["bb_mid"]) or (position["type"] == "short" and price <= row["bb_mid"]):
                    pnl_pct -= self.total_cost * 200
                    trades.append({**self._make_trade(symbol, position, price, row, pnl_pct, "mean_revert")})
                    position = None
                elif (position["type"] == "long" and price < row["bb_lower"] * 0.98) or (position["type"] == "short" and price > row["bb_upper"] * 1.02):
                    pnl_pct -= self.total_cost * 200
                    trades.append({**self._make_trade(symbol, position, price, row, pnl_pct, "stop_loss")})
                    position = None
            
            if not position:
                if price < row["bb_lower"]:
                    position = {"type": "long", "entry": price, "date": row.name}
                elif price > row["bb_upper"]:
                    position = {"type": "short", "entry": price, "date": row.name}
        
        return trades
    
    def _backtest_combined(self, df: pd.DataFrame, symbol: str, position_pct: float) -> List[Dict]:
        """Combined: merge all strategies, remove overlaps."""
        all_trades = sorted(
            self._backtest_rule_based(df, symbol, position_pct)
            + self._backtest_momentum(df, symbol, position_pct)
            + self._backtest_mean_reversion(df, symbol, position_pct),
            key=lambda t: t.get("entry_date", ""),
        )
        filtered = []
        last_exit = None
        for trade in all_trades:
            if last_exit and trade.get("entry_date", "") <= last_exit:
                continue
            filtered.append(trade)
            last_exit = trade.get("exit_date", "")
        return filtered
    
    def _make_trade(self, symbol, position, exit_price, row, pnl, reason) -> Dict:
        return {
            "symbol": symbol, "type": position["type"],
            "entry_price": round(position["entry"], 2),
            "exit_price": round(exit_price, 2),
            "entry_date": str(position["date"]),
            "exit_date": str(row.name),
            "pnl_percent": round(pnl, 2), "exit_reason": reason,
        }
    
    def _calc_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        TRADING FIX #5: Wilder's smoothing RSI — matches live indicator service.
        Previous backtest used simple rolling mean (different from live).
        """
        delta = prices.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        
        # Wilder's smoothing (exponential, alpha=1/period)
        avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _calc_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate ATR for volatility-adjusted stops."""
        high_low = df["High"] - df["Low"]
        high_close = abs(df["High"] - df["Close"].shift())
        low_close = abs(df["Low"] - df["Close"].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(period).mean()
    
    def _calculate_metrics(self, trades: List[Dict], initial_capital: float) -> Dict:
        """Calculate comprehensive backtest metrics."""
        if not trades:
            return {
                "total_trades": 0, "winning_trades": 0, "losing_trades": 0,
                "win_rate": 0, "avg_profit": 0, "avg_loss": 0,
                "profit_factor": 0, "total_return": 0, "max_drawdown": 0,
                "sharpe_ratio": 0, "avg_holding_days": 0, "best_trade": 0, "worst_trade": 0,
            }
        
        wins = [t for t in trades if t["pnl_percent"] > 0]
        losses = [t for t in trades if t["pnl_percent"] <= 0]
        
        total_return = sum(t["pnl_percent"] for t in trades)
        avg_profit = float(np.mean([t["pnl_percent"] for t in wins])) if wins else 0
        avg_loss = float(np.mean([t["pnl_percent"] for t in losses])) if losses else 0
        
        gross_profit = sum(t["pnl_percent"] for t in wins) if wins else 0
        gross_loss = abs(sum(t["pnl_percent"] for t in losses)) if losses else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
        
        # Max drawdown
        cumulative = 0
        peak = 0
        max_dd = 0
        for t in trades:
            cumulative += t["pnl_percent"]
            peak = max(peak, cumulative)
            max_dd = max(max_dd, peak - cumulative)
        
        # Sharpe
        returns = [t["pnl_percent"] for t in trades]
        sharpe = float(np.mean(returns) / np.std(returns) * np.sqrt(252)) if np.std(returns) > 0 else 0
        
        holding_days = [t.get("holding_days", 0) for t in trades if t.get("holding_days")]
        
        return {
            "total_trades": len(trades),
            "winning_trades": len(wins), "losing_trades": len(losses),
            "win_rate": round(len(wins) / len(trades) * 100, 1),
            "avg_profit": round(avg_profit, 2), "avg_loss": round(avg_loss, 2),
            "profit_factor": round(min(profit_factor, 999), 2),
            "total_return": round(total_return, 2),
            "max_drawdown": round(max_dd, 2),
            "sharpe_ratio": round(sharpe, 2),
            "avg_holding_days": round(float(np.mean(holding_days)), 1) if holding_days else 0,
            "best_trade": round(max(t["pnl_percent"] for t in trades), 2),
            "worst_trade": round(min(t["pnl_percent"] for t in trades), 2),
        }


# Singleton
backtest_engine = BacktestEngine()
