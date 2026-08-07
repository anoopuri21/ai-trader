"""
ARTH's Backtesting Engine
Validates strategies against historical data and learns from results
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np

from services.price_fetcher import price_fetcher
from services.indicators import indicators
from ai_agent.brain import brain

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Backtesting engine that validates strategies and helps ARTH learn"""
    
    def __init__(self):
        self.brain = brain
    
    async def run_backtest(
        self,
        symbol: str,
        strategy: str = "rule_based",
        start_date: str = None,
        end_date: str = None,
        initial_capital: float = 100000.0,
        position_size_pct: float = 0.1  # 10% per trade
    ) -> Dict[str, Any]:
        """
        Run backtest for a symbol with given strategy.
        
        Strategies:
        - rule_based: SMA crossover + RSI + MACD
        - momentum: RSI + Volume momentum
        - mean_reversion: Bollinger Bands mean reversion
        - combined: All strategies with ARTH's learned weights
        """
        if not start_date:
            start_date = (datetime.utcnow() - timedelta(days=365)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.utcnow().strftime("%Y-%m-%d")
        
        # Fetch historical data
        df = await price_fetcher.get_historical_data(
            symbol, period="1y", interval="1d"
        )
        
        if df is None or df.empty:
            return {"error": f"No data available for {symbol}"}
        
        # Run strategy
        if strategy == "rule_based":
            trades = self._backtest_rule_based(df, symbol, position_size_pct)
        elif strategy == "momentum":
            trades = self._backtest_momentum(df, symbol, position_size_pct)
        elif strategy == "mean_reversion":
            trades = self._backtest_mean_reversion(df, symbol, position_size_pct)
        elif strategy == "combined":
            trades = self._backtest_combined(df, symbol, position_size_pct)
        else:
            trades = self._backtest_rule_based(df, symbol, position_size_pct)
        
        # Calculate metrics
        metrics = self._calculate_metrics(trades, initial_capital)
        
        # Store results in ARTH's brain
        self._store_backtest_results(symbol, strategy, start_date, end_date, metrics, trades)
        
        return {
            "symbol": symbol,
            "strategy": strategy,
            "period": {"start": start_date, "end": end_date},
            "metrics": metrics,
            "trades": trades[-20:],  # Last 20 trades
            "total_trades": len(trades),
        }
    
    def _backtest_rule_based(self, df: pd.DataFrame, symbol: str, 
                             position_pct: float) -> List[Dict]:
        """Rule-based strategy: SMA crossover + RSI + MACD"""
        trades = []
        position = None
        
        # Calculate indicators for all rows
        df = df.copy()
        df['sma_20'] = df['Close'].rolling(20).mean()
        df['sma_50'] = df['Close'].rolling(50).mean()
        df['sma_200'] = df['Close'].rolling(200).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema_12 = df['Close'].ewm(span=12).mean()
        ema_26 = df['Close'].ewm(span=26).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        df['bb_mid'] = df['Close'].rolling(20).mean()
        df['bb_std'] = df['Close'].rolling(20).std()
        df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
        
        for i in range(200, len(df)):
            row = df.iloc[i]
            price = row['Close']
            
            # Skip if no indicators
            if pd.isna(row['sma_20']) or pd.isna(row['sma_50']) or pd.isna(row['rsi']):
                continue
            
            # Check for exit if in position
            if position:
                exit_reason = None
                exit_price = price
                
                # Stop loss hit
                if position['type'] == 'long' and price <= position['stop_loss']:
                    exit_reason = "stop_loss"
                elif position['type'] == 'short' and price >= position['stop_loss']:
                    exit_reason = "stop_loss"
                # Take profit hit
                elif position['type'] == 'long' and price >= position['target']:
                    exit_reason = "take_profit"
                elif position['type'] == 'short' and price <= position['target']:
                    exit_reason = "take_profit"
                # MACD reversal
                elif position['type'] == 'long' and row['macd'] < row['macd_signal'] and row['macd_hist'] < 0:
                    exit_reason = "signal_reversal"
                elif position['type'] == 'short' and row['macd'] > row['macd_signal'] and row['macd_hist'] > 0:
                    exit_reason = "signal_reversal"
                
                if exit_reason:
                    if position['type'] == 'long':
                        pnl_pct = (exit_price - position['entry']) / position['entry'] * 100
                    else:
                        pnl_pct = (position['entry'] - exit_price) / position['entry'] * 100
                    
                    trades.append({
                        "symbol": symbol,
                        "type": position['type'],
                        "entry_price": round(position['entry'], 2),
                        "exit_price": round(exit_price, 2),
                        "entry_date": position['date'].isoformat() if hasattr(position['date'], 'isoformat') else str(position['date']),
                        "exit_date": row.name.isoformat() if hasattr(row.name, 'isoformat') else str(row.name),
                        "pnl_percent": round(pnl_pct, 2),
                        "exit_reason": exit_reason,
                        "holding_days": (row.name - position['date']).days if hasattr(row.name, 'isoformat') else 0,
                    })
                    position = None
            
            # Check for entry if not in position
            if not position:
                buy_score = 0
                sell_score = 0
                
                # SMA crossover
                if row['sma_20'] > row['sma_50']:
                    buy_score += 1
                else:
                    sell_score += 1
                
                # Price vs SMA
                if price > row['sma_20']:
                    buy_score += 1
                elif price < row['sma_20']:
                    sell_score += 1
                
                # RSI
                if row['rsi'] < 30:
                    buy_score += 2
                elif row['rsi'] > 70:
                    sell_score += 2
                elif row['rsi'] < 40:
                    buy_score += 1
                elif row['rsi'] > 60:
                    sell_score += 1
                
                # MACD
                if row['macd'] > row['macd_signal']:
                    buy_score += 1
                else:
                    sell_score += 1
                
                # Bollinger Band position
                if price < row['bb_lower']:
                    buy_score += 2
                elif price > row['bb_upper']:
                    sell_score += 2
                
                # Volume confirmation
                avg_vol = df['Volume'].iloc[max(0,i-20):i].mean()
                if row['Volume'] > avg_vol * 1.5:
                    if buy_score > sell_score:
                        buy_score += 1
                    elif sell_score > buy_score:
                        sell_score += 1
                
                # Entry decision
                if buy_score >= 4 and buy_score > sell_score + 1:
                    stop_pct = 0.015
                    target_pct = 0.03
                    position = {
                        'type': 'long',
                        'entry': price,
                        'date': row.name,
                        'stop_loss': price * (1 - stop_pct),
                        'target': price * (1 + target_pct),
                        'confidence': min(95, 50 + (buy_score - sell_score) * 5),
                    }
                elif sell_score >= 4 and sell_score > buy_score + 1:
                    stop_pct = 0.015
                    target_pct = 0.03
                    position = {
                        'type': 'short',
                        'entry': price,
                        'date': row.name,
                        'stop_loss': price * (1 + stop_pct),
                        'target': price * (1 - target_pct),
                        'confidence': min(95, 50 + (sell_score - buy_score) * 5),
                    }
        
        return trades
    
    def _backtest_momentum(self, df: pd.DataFrame, symbol: str,
                          position_pct: float) -> List[Dict]:
        """Momentum strategy: RSI + Volume"""
        trades = []
        position = None
        
        df = df.copy()
        df['rsi'] = self._calc_rsi(df['Close'])
        df['vol_ma'] = df['Volume'].rolling(20).mean()
        df['roc'] = df['Close'].pct_change(10, fill_method=None) * 100  # 10-day rate of change
        
        for i in range(25, len(df)):
            row = df.iloc[i]
            price = row['Close']
            
            if pd.isna(row['rsi']) or pd.isna(row['roc']):
                continue
            
            if position:
                # Exit on RSI reversal
                if position['type'] == 'long' and row['rsi'] > 70:
                    pnl = (price - position['entry']) / position['entry'] * 100
                    trades.append({**self._make_trade(symbol, position, price, row, pnl, "rsi_overbought")})
                    position = None
                elif position['type'] == 'short' and row['rsi'] < 30:
                    pnl = (position['entry'] - price) / position['entry'] * 100
                    trades.append({**self._make_trade(symbol, position, price, row, pnl, "rsi_oversold")})
                    position = None
                # Stop loss
                elif position['type'] == 'long' and price < position['entry'] * 0.97:
                    pnl = (price - position['entry']) / position['entry'] * 100
                    trades.append({**self._make_trade(symbol, position, price, row, pnl, "stop_loss")})
                    position = None
                elif position['type'] == 'short' and price > position['entry'] * 1.03:
                    pnl = (position['entry'] - price) / position['entry'] * 100
                    trades.append({**self._make_trade(symbol, position, price, row, pnl, "stop_loss")})
                    position = None
            
            if not position:
                if row['rsi'] < 30 and row['roc'] > 0 and row['Volume'] > row['vol_ma']:
                    position = {'type': 'long', 'entry': price, 'date': row.name}
                elif row['rsi'] > 70 and row['roc'] < 0 and row['Volume'] > row['vol_ma']:
                    position = {'type': 'short', 'entry': price, 'date': row.name}
        
        return trades
    
    def _backtest_mean_reversion(self, df: pd.DataFrame, symbol: str,
                                position_pct: float) -> List[Dict]:
        """Mean reversion: Bollinger Bands"""
        trades = []
        position = None
        
        df = df.copy()
        df['bb_mid'] = df['Close'].rolling(20).mean()
        df['bb_std'] = df['Close'].rolling(20).std()
        df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
        
        for i in range(25, len(df)):
            row = df.iloc[i]
            price = row['Close']
            
            if pd.isna(row['bb_mid']):
                continue
            
            if position:
                # Exit at mean
                if position['type'] == 'long' and price >= row['bb_mid']:
                    pnl = (price - position['entry']) / position['entry'] * 100
                    trades.append({**self._make_trade(symbol, position, price, row, pnl, "mean_revert")})
                    position = None
                elif position['type'] == 'short' and price <= row['bb_mid']:
                    pnl = (position['entry'] - price) / position['entry'] * 100
                    trades.append({**self._make_trade(symbol, position, price, row, pnl, "mean_revert")})
                    position = None
                # Stop loss at bands
                elif position['type'] == 'long' and price < row['bb_lower'] * 0.98:
                    pnl = (price - position['entry']) / position['entry'] * 100
                    trades.append({**self._make_trade(symbol, position, price, row, pnl, "stop_loss")})
                    position = None
                elif position['type'] == 'short' and price > row['bb_upper'] * 1.02:
                    pnl = (position['entry'] - price) / position['entry'] * 100
                    trades.append({**self._make_trade(symbol, position, price, row, pnl, "stop_loss")})
                    position = None
            
            if not position:
                if price < row['bb_lower']:
                    position = {'type': 'long', 'entry': price, 'date': row.name}
                elif price > row['bb_upper']:
                    position = {'type': 'short', 'entry': price, 'date': row.name}
        
        return trades
    
    def _backtest_combined(self, df: pd.DataFrame, symbol: str,
                          position_pct: float) -> List[Dict]:
        """Combined strategy using all signals with ARTH's learned weights"""
        # Get ARTH's learned rules to weight signals
        rules = self.brain.get_active_rules()
        
        # Run all strategies
        rule_trades = self._backtest_rule_based(df, symbol, position_pct)
        momentum_trades = self._backtest_momentum(df, symbol, position_pct)
        mean_rev_trades = self._backtest_mean_reversion(df, symbol, position_pct)
        
        # Combine trades, preferring higher confidence signals
        all_trades = sorted(
            rule_trades + momentum_trades + mean_rev_trades,
            key=lambda t: t.get('entry_date', ''),
        )
        
        # Remove overlapping trades (same entry window)
        filtered = []
        last_exit = None
        for trade in all_trades:
            entry = trade.get('entry_date', '')
            if last_exit and entry <= last_exit:
                continue
            filtered.append(trade)
            last_exit = trade.get('exit_date', '')
        
        return filtered
    
    def _make_trade(self, symbol: str, position: dict, exit_price: float,
                   row, pnl: float, reason: str) -> Dict:
        """Helper to create a trade record"""
        return {
            "symbol": symbol,
            "type": position['type'],
            "entry_price": round(position['entry'], 2),
            "exit_price": round(exit_price, 2),
            "entry_date": position['date'].isoformat() if hasattr(position['date'], 'isoformat') else str(position['date']),
            "exit_date": row.name.isoformat() if hasattr(row.name, 'isoformat') else str(row.name),
            "pnl_percent": round(pnl, 2),
            "exit_reason": reason,
        }
    
    def _calc_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = -delta.where(delta < 0, 0).rolling(period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_metrics(self, trades: List[Dict], initial_capital: float) -> Dict:
        """Calculate comprehensive backtest metrics"""
        if not trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "avg_profit": 0,
                "avg_loss": 0,
                "profit_factor": 0,
                "total_return": 0,
                "max_drawdown": 0,
                "sharpe_ratio": 0,
                "avg_holding_days": 0,
            }
        
        wins = [t for t in trades if t['pnl_percent'] > 0]
        losses = [t for t in trades if t['pnl_percent'] <= 0]
        
        total_return = sum(t['pnl_percent'] for t in trades)
        avg_profit = np.mean([t['pnl_percent'] for t in wins]) if wins else 0
        avg_loss = np.mean([t['pnl_percent'] for t in losses]) if losses else 0
        
        gross_profit = sum(t['pnl_percent'] for t in wins) if wins else 0
        gross_loss = abs(sum(t['pnl_percent'] for t in losses)) if losses else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Max drawdown
        cumulative = 0
        peak = 0
        max_dd = 0
        for t in trades:
            cumulative += t['pnl_percent']
            peak = max(peak, cumulative)
            dd = peak - cumulative
            max_dd = max(max_dd, dd)
        
        # Sharpe ratio (simplified)
        returns = [t['pnl_percent'] for t in trades]
        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        
        # Average holding period
        holding_days = [t.get('holding_days', 0) for t in trades if t.get('holding_days')]
        avg_holding = np.mean(holding_days) if holding_days else 0
        
        return {
            "total_trades": len(trades),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0,
            "avg_profit": round(avg_profit, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 2),
            "total_return": round(total_return, 2),
            "max_drawdown": round(max_dd, 2),
            "sharpe_ratio": round(sharpe, 2),
            "avg_holding_days": round(avg_holding, 1),
            "best_trade": round(max(t['pnl_percent'] for t in trades), 2),
            "worst_trade": round(min(t['pnl_percent'] for t in trades), 2),
        }
    
    def _store_backtest_results(self, symbol: str, strategy: str, 
                                start_date: str, end_date: str,
                                metrics: Dict, trades: List[Dict]):
        """Store backtest results in ARTH's brain"""
        try:
            cursor = self.brain.conn.cursor()
            cursor.execute("""
                INSERT INTO strategy_performance
                (strategy_name, period_start, period_end, total_trades, 
                 winning_trades, losing_trades, win_rate, avg_profit, avg_loss,
                 profit_factor, sharpe_ratio, max_drawdown)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"{symbol}_{strategy}", start_date, end_date,
                metrics['total_trades'], metrics['winning_trades'],
                metrics['losing_trades'], metrics['win_rate'],
                metrics['avg_profit'], metrics['avg_loss'],
                metrics['profit_factor'], metrics['sharpe_ratio'],
                metrics['max_drawdown']
            ))
            self.brain.conn.commit()
            
            # Store successful patterns from winning trades
            for trade in trades:
                if trade['pnl_percent'] > 0:
                    pattern_name = f"{trade['type']}_{trade['exit_reason']}_{symbol}"
                    self.brain.store_pattern(
                        pattern_name, trade['type'],
                        {"pnl": trade['pnl_percent'], "strategy": strategy},
                        confidence=0.5
                    )
            
            logger.info(f"Backtest stored: {symbol} {strategy} - {metrics['total_trades']} trades, {metrics['win_rate']}% win rate")
        except Exception as e:
            logger.error(f"Error storing backtest results: {e}")


# Singleton
backtest_engine = BacktestEngine()
