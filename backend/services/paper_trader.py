"""
Paper Trading Simulator

Architecture Fix: Uses centralized DatabaseManager instead of creating
its own SQLite file. All paper trading data is in the same database as
ARTH's brain, backtest results, and market context.
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PaperTrader:
    """Virtual portfolio for testing trading signals."""
    
    def __init__(self):
        from database.manager import get_db
        self.db = get_db()
        self.initial_capital = 100000.0
        logger.info("PaperTrader initialized (using centralized DB)")
    
    @property
    def conn(self):
        """Backward compat — some code accesses .conn directly."""
        return self.db.conn
    
    def open_position(self, symbol: str, signal: str, price: float,
                     confidence: int = 70, stop_loss: float = None,
                     target: float = None, allocation_pct: float = 0.1) -> Dict:
        """Open a new paper position."""
        portfolio = self._get_portfolio_row()
        cash = portfolio["current_cash"]
        
        # Scale allocation by confidence
        if confidence >= 80:
            alloc_pct = min(allocation_pct * 1.5, 0.20)
        elif confidence < 50:
            alloc_pct = allocation_pct * 0.5
        else:
            alloc_pct = allocation_pct
        
        alloc_amount = cash * alloc_pct
        quantity = int(alloc_amount / price)
        
        if quantity < 1:
            return {"error": "Insufficient funds for even 1 share"}
        
        cost = quantity * price
        if cost > cash:
            quantity = int(cash / price)
            cost = quantity * price
        
        new_cash = cash - cost
        self.db.execute(
            "UPDATE paper_portfolio SET current_cash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_cash, portfolio["id"]),
        )
        
        self.db.execute_insert(
            """INSERT INTO paper_positions 
            (symbol, type, quantity, entry_price, current_price, stop_loss, target_price, signal_confidence, signal_source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (symbol, signal.upper(), quantity, price, price, stop_loss, target, confidence, "ARTH"),
        )
        
        return {
            "status": "opened", "symbol": symbol, "type": signal.upper(),
            "quantity": quantity, "entry_price": price,
            "cost": round(cost, 2), "remaining_cash": round(new_cash, 2),
            "allocation_pct": round(cost / cash * 100, 1) if cash > 0 else 0,
        }
    
    def close_position(self, position_id: int, exit_price: float, reason: str = "manual") -> Dict:
        """Close an open paper position."""
        rows = self.db.execute_read(
            "SELECT * FROM paper_positions WHERE id = ? AND status = 'OPEN'", (position_id,)
        )
        if not rows:
            return {"error": "Position not found or already closed"}
        
        pos = dict(rows[0])
        
        if pos["type"] == "LONG":
            pnl = (exit_price - pos["entry_price"]) * pos["quantity"]
            pnl_pct = (exit_price - pos["entry_price"]) / pos["entry_price"] * 100
        else:
            pnl = (pos["entry_price"] - exit_price) * pos["quantity"]
            pnl_pct = (pos["entry_price"] - exit_price) / pos["entry_price"] * 100
        
        proceeds = pos["quantity"] * exit_price
        portfolio = self._get_portfolio_row()
        
        self.db.execute(
            "UPDATE paper_portfolio SET current_cash = current_cash + ?, total_pnl = total_pnl + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (proceeds, pnl, portfolio["id"]),
        )
        
        self.db.execute(
            "UPDATE paper_positions SET status = 'CLOSED', current_price = ?, unrealized_pnl = ? WHERE id = ?",
            (exit_price, round(pnl, 2), position_id),
        )
        
        self.db.execute_insert(
            """INSERT INTO paper_trades 
            (symbol, type, quantity, entry_price, exit_price, pnl, pnl_percent, exit_reason, opened_at, closed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (pos["symbol"], pos["type"], pos["quantity"], pos["entry_price"],
             exit_price, round(pnl, 2), round(pnl_pct, 2), reason, pos["opened_at"]),
        )
        
        return {"status": "closed", "symbol": pos["symbol"], "pnl": round(pnl, 2), "pnl_percent": round(pnl_pct, 2), "reason": reason}
    
    def update_prices(self, prices: Dict[str, float]):
        """Update current prices for open positions."""
        positions = self.db.execute_read("SELECT * FROM paper_positions WHERE status = 'OPEN'")
        for pos in positions:
            if pos["symbol"] in prices:
                p = prices[pos["symbol"]]
                unrealized = ((p - pos["entry_price"]) if pos["type"] == "LONG" else (pos["entry_price"] - p)) * pos["quantity"]
                self.db.execute(
                    "UPDATE paper_positions SET current_price = ?, unrealized_pnl = ? WHERE id = ?",
                    (p, round(unrealized, 2), pos["id"]),
                )
    
    def get_portfolio(self) -> Dict:
        """Get current portfolio status."""
        portfolio = self._get_portfolio_row()
        open_positions = [dict(p) for p in self.db.execute_read("SELECT * FROM paper_positions WHERE status = 'OPEN'")]
        
        unrealized = sum(p.get("unrealized_pnl", 0) for p in open_positions)
        total_value = portfolio["current_cash"] + sum(
            p["quantity"] * (p["current_price"] or p["entry_price"]) for p in open_positions
        )
        
        total_pnl = total_value - portfolio["initial_capital"]
        total_pnl_pct = (total_pnl / portfolio["initial_capital"]) * 100 if portfolio["initial_capital"] > 0 else 0
        
        self.db.execute(
            "UPDATE paper_portfolio SET total_value = ?, total_pnl = ?, total_pnl_percent = ? WHERE id = ?",
            (round(total_value, 2), round(total_pnl, 2), round(total_pnl_pct, 2), portfolio["id"]),
        )
        
        return {
            "initial_capital": portfolio["initial_capital"],
            "current_cash": round(portfolio["current_cash"], 2),
            "total_value": round(total_value, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_percent": round(total_pnl_pct, 2),
            "unrealized_pnl": round(unrealized, 2),
            "open_positions": len(open_positions),
            "positions": open_positions,
        }
    
    def get_trade_history(self, limit: int = 50) -> List[Dict]:
        rows = self.db.execute_read("SELECT * FROM paper_trades ORDER BY closed_at DESC LIMIT ?", (limit,))
        return [dict(r) for r in rows]
    
    def get_performance(self) -> Dict:
        rows = self.db.execute_read("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) as losses,
                   AVG(pnl_percent) as avg_return, SUM(pnl) as total_pnl,
                   MAX(pnl_percent) as best_trade, MIN(pnl_percent) as worst_trade
            FROM paper_trades
        """)
        row = dict(rows[0]) if rows else {}
        
        if not row.get("total"):
            return {"total_trades": 0, "message": "No trades yet"}
        
        return {
            "total_trades": row["total"], "winning_trades": row["wins"] or 0,
            "losing_trades": row["losses"] or 0,
            "win_rate": round((row["wins"] or 0) / row["total"] * 100, 1),
            "avg_return": round(row["avg_return"] or 0, 2),
            "total_pnl": round(row["total_pnl"] or 0, 2),
            "best_trade": round(row["best_trade"] or 0, 2),
            "worst_trade": round(row["worst_trade"] or 0, 2),
        }
    
    def _get_portfolio_row(self) -> Dict:
        rows = self.db.execute_read("SELECT * FROM paper_portfolio ORDER BY id DESC LIMIT 1")
        return dict(rows[0]) if rows else {"id": 1, "initial_capital": 100000, "current_cash": 100000, "total_value": 100000}
    
    def close(self):
        pass  # DB managed centrally


# Singleton
paper_trader = PaperTrader()
