"""
Paper Trading Simulator
Virtual portfolio to test ARTH's signals without real money
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class PaperTrader:
    """Virtual portfolio for testing trading signals"""
    
    def __init__(self, db_path: str = "paper_trading.db"):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self.initial_capital = 100000.0  # ₹1,00,000
        self._init_db()
    
    def _init_db(self):
        """Initialize paper trading database"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                initial_capital REAL NOT NULL,
                current_cash REAL NOT NULL,
                total_value REAL NOT NULL,
                total_pnl REAL DEFAULT 0,
                total_pnl_percent REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                type TEXT NOT NULL,  -- LONG or SHORT
                quantity INTEGER NOT NULL,
                entry_price REAL NOT NULL,
                current_price REAL,
                unrealized_pnl REAL DEFAULT 0,
                stop_loss REAL,
                target_price REAL,
                signal_confidence INTEGER,
                signal_source TEXT,
                opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'OPEN'
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                pnl REAL DEFAULT 0,
                pnl_percent REAL DEFAULT 0,
                exit_reason TEXT,
                signal_id INTEGER,
                opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP
            )
        """)
        
        # Initialize portfolio if not exists
        cursor.execute("SELECT COUNT(*) FROM portfolio")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO portfolio (initial_capital, current_cash, total_value)
                VALUES (?, ?, ?)
            """, (self.initial_capital, self.initial_capital, self.initial_capital))
            self.conn.commit()
        
        logger.info("Paper trading initialized")
    
    def open_position(self, symbol: str, signal: str, price: float, 
                     confidence: int = 70, stop_loss: float = None,
                     target: float = None, allocation_pct: float = 0.1) -> Dict:
        """Open a new paper position"""
        cursor = self.conn.cursor()
        
        # Get current cash
        cursor.execute("SELECT current_cash FROM portfolio ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        cash = row['current_cash']
        
        # Calculate position size
        alloc_amount = cash * allocation_pct
        
        # Adjust by confidence
        if confidence >= 80:
            alloc_amount = cash * min(allocation_pct * 1.5, 0.2)
        elif confidence < 50:
            alloc_amount = cash * allocation_pct * 0.5
        
        quantity = int(alloc_amount / price)
        if quantity < 1:
            return {"error": "Insufficient funds for even 1 share"}
        
        cost = quantity * price
        
        if cost > cash:
            quantity = int(cash / price)
            cost = quantity * price
        
        # Deduct from cash
        new_cash = cash - cost
        cursor.execute("""
            UPDATE portfolio SET current_cash = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = (SELECT MAX(id) FROM portfolio)
        """, (new_cash,))
        
        # Open position
        cursor.execute("""
            INSERT INTO positions (symbol, type, quantity, entry_price, current_price,
                                 stop_loss, target_price, signal_confidence, signal_source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (symbol, signal.upper(), quantity, price, price,
              stop_loss, target, confidence, "ARTH"))
        
        self.conn.commit()
        
        return {
            "status": "opened",
            "symbol": symbol,
            "type": signal.upper(),
            "quantity": quantity,
            "entry_price": price,
            "cost": round(cost, 2),
            "remaining_cash": round(new_cash, 2),
            "allocation_pct": round(cost / cash * 100, 1),
        }
    
    def close_position(self, position_id: int, exit_price: float, reason: str = "manual") -> Dict:
        """Close an open position"""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT * FROM positions WHERE id = ? AND status = 'OPEN'", (position_id,))
        pos = cursor.fetchone()
        if not pos:
            return {"error": "Position not found or already closed"}
        
        # Calculate P&L
        if pos['type'] == 'LONG':
            pnl = (exit_price - pos['entry_price']) * pos['quantity']
        else:
            pnl = (pos['entry_price'] - exit_price) * pos['quantity']
        
        pnl_pct = (exit_price - pos['entry_price']) / pos['entry_price'] * 100 if pos['type'] == 'LONG' \
            else (pos['entry_price'] - exit_price) / pos['entry_price'] * 100
        
        # Add back to cash
        proceeds = pos['quantity'] * exit_price
        cursor.execute("""
            UPDATE portfolio SET current_cash = current_cash + ?, 
                                total_pnl = total_pnl + ?,
                                updated_at = CURRENT_TIMESTAMP
            WHERE id = (SELECT MAX(id) FROM portfolio)
        """, (proceeds, pnl))
        
        # Close position
        cursor.execute("""
            UPDATE positions SET status = 'CLOSED', current_price = ?, 
                               unrealized_pnl = ? WHERE id = ?
        """, (exit_price, pnl, position_id))
        
        # Record trade
        cursor.execute("""
            INSERT INTO trades (symbol, type, quantity, entry_price, exit_price,
                              pnl, pnl_percent, exit_reason, opened_at, closed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (pos['symbol'], pos['type'], pos['quantity'], pos['entry_price'],
              exit_price, round(pnl, 2), round(pnl_pct, 2), reason, pos['opened_at']))
        
        self.conn.commit()
        
        return {
            "status": "closed",
            "symbol": pos['symbol'],
            "pnl": round(pnl, 2),
            "pnl_percent": round(pnl_pct, 2),
            "reason": reason,
        }
    
    def update_prices(self, prices: Dict[str, float]):
        """Update current prices for open positions"""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT * FROM positions WHERE status = 'OPEN'")
        positions = cursor.fetchall()
        
        for pos in positions:
            if pos['symbol'] in prices:
                new_price = prices[pos['symbol']]
                if pos['type'] == 'LONG':
                    unrealized = (new_price - pos['entry_price']) * pos['quantity']
                else:
                    unrealized = (pos['entry_price'] - new_price) * pos['quantity']
                
                cursor.execute("""
                    UPDATE positions SET current_price = ?, unrealized_pnl = ?
                    WHERE id = ?
                """, (new_price, round(unrealized, 2), pos['id']))
        
        self.conn.commit()
    
    def get_portfolio(self) -> Dict:
        """Get current portfolio status"""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT * FROM portfolio ORDER BY id DESC LIMIT 1")
        portfolio = dict(cursor.fetchone())
        
        cursor.execute("SELECT * FROM positions WHERE status = 'OPEN'")
        open_positions = [dict(p) for p in cursor.fetchall()]
        
        # Calculate total value
        unrealized_pnl = sum(p.get('unrealized_pnl', 0) for p in open_positions)
        total_value = portfolio['current_cash'] + sum(
            p['quantity'] * (p['current_price'] or p['entry_price']) for p in open_positions
        )
        
        # Update portfolio total
        total_pnl = total_value - portfolio['initial_capital']
        total_pnl_pct = (total_pnl / portfolio['initial_capital']) * 100
        
        cursor.execute("""
            UPDATE portfolio SET total_value = ?, total_pnl = ?, total_pnl_percent = ?
            WHERE id = (SELECT MAX(id) FROM portfolio)
        """, (round(total_value, 2), round(total_pnl, 2), round(total_pnl_pct, 2)))
        self.conn.commit()
        
        return {
            "initial_capital": portfolio['initial_capital'],
            "current_cash": round(portfolio['current_cash'], 2),
            "total_value": round(total_value, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_percent": round(total_pnl_pct, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "open_positions": len(open_positions),
            "positions": open_positions,
        }
    
    def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """Get trade history"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM trades ORDER BY closed_at DESC LIMIT ?", (limit,))
        return [dict(t) for t in cursor.fetchall()]
    
    def get_performance(self) -> Dict:
        """Get overall performance metrics"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) as losses,
                   AVG(pnl_percent) as avg_return,
                   SUM(pnl) as total_pnl,
                   MAX(pnl_percent) as best_trade,
                   MIN(pnl_percent) as worst_trade
            FROM trades
        """)
        row = cursor.fetchone()
        
        if not row or row['total'] == 0:
            return {"total_trades": 0, "message": "No trades yet"}
        
        wins = row['wins'] or 0
        losses = row['losses'] or 0
        total = row['total']
        
        return {
            "total_trades": total,
            "winning_trades": wins,
            "losing_trades": losses,
            "win_rate": round(wins / total * 100, 1),
            "avg_return": round(row['avg_return'] or 0, 2),
            "total_pnl": round(row['total_pnl'] or 0, 2),
            "best_trade": round(row['best_trade'] or 0, 2),
            "worst_trade": round(row['worst_trade'] or 0, 2),
        }
    
    def close(self):
        if self.conn:
            self.conn.close()


# Singleton
paper_trader = PaperTrader()
