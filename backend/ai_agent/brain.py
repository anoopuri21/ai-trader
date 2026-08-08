"""
ARTH's Brain — Central Knowledge Base

Architecture: Uses the centralized DatabaseManager instead of creating
its own SQLite connection. All brain data lives in the same database file
as paper trading, backtesting, and market context data.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ArthBrain:
    """
    ARTH's central knowledge base.
    
    Delegates all DB operations to the centralized DatabaseManager
    which provides thread-safe writes and a single database file.
    """
    
    def __init__(self):
        from database.manager import get_db
        self.db = get_db()
        logger.info("ArthBrain initialized (using centralized DB)")
    
    # ─── PREDICTIONS ─────────────────────────────────────────────
    
    def store_prediction(
        self,
        symbol: str,
        signal: str,
        confidence: int,
        entry_price: float = None,
        target_price: float = None,
        stop_loss: float = None,
        indicators: dict = None,
        ai_provider: str = None,
        ai_reasoning: str = None,
        pattern_used: str = None,
        timeframe: str = "SWING",
    ) -> int:
        """Store a new prediction and return its ID."""
        return self.db.execute_insert(
            """
            INSERT INTO predictions 
            (symbol, signal, confidence, entry_price, target_price, stop_loss,
             indicators_snapshot, ai_provider, ai_reasoning, pattern_used, timeframe)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                symbol, signal, confidence, entry_price, target_price, stop_loss,
                json.dumps(indicators) if indicators else None,
                ai_provider, ai_reasoning, pattern_used, timeframe,
            ),
        )
    
    def resolve_prediction(self, prediction_id: int, outcome: str, actual_return: float):
        """Resolve a prediction with actual outcome."""
        self.db.execute(
            """
            UPDATE predictions 
            SET outcome = ?, actual_return = ?, was_correct = ?, resolved_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (outcome, actual_return, 1 if outcome == "WIN" else 0, prediction_id),
        )
        
        # Update pattern success if applicable
        rows = self.db.execute_read(
            "SELECT pattern_used FROM predictions WHERE id = ?", (prediction_id,)
        )
        if rows and rows[0]["pattern_used"]:
            self._update_pattern_success(rows[0]["pattern_used"], 1 if outcome == "WIN" else 0)
    
    def get_unresolved_predictions(self, days_old: int = 1) -> List[Dict]:
        """Get predictions that haven't been resolved yet."""
        cutoff = (datetime.utcnow() - timedelta(days=days_old)).isoformat()
        rows = self.db.execute_read(
            """
            SELECT * FROM predictions 
            WHERE outcome IS NULL AND predicted_at < ?
            ORDER BY predicted_at DESC
            """,
            (cutoff,),
        )
        return [dict(r) for r in rows]
    
    def get_recent_predictions(self, limit: int = 50) -> List[Dict]:
        rows = self.db.execute_read(
            "SELECT * FROM predictions ORDER BY predicted_at DESC LIMIT ?", (limit,)
        )
        return [dict(r) for r in rows]
    
    def get_prediction_accuracy(self, days: int = 30) -> Dict:
        """Get prediction accuracy for last N days."""
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        rows = self.db.execute_read(
            """
            SELECT 
                COUNT(*) as total,
                SUM(was_correct) as correct,
                AVG(CASE WHEN was_correct = 1 THEN actual_return ELSE NULL END) as avg_win,
                AVG(CASE WHEN was_correct = 0 THEN actual_return ELSE NULL END) as avg_loss,
                AVG(confidence) as avg_confidence
            FROM predictions 
            WHERE outcome IS NOT NULL AND predicted_at > ?
            """,
            (cutoff,),
        )
        row = rows[0] if rows else None
        if row and row["total"] and row["total"] > 0:
            return {
                "total_predictions": row["total"],
                "correct_predictions": row["correct"] or 0,
                "accuracy": round((row["correct"] or 0) / row["total"] * 100, 1),
                "avg_win_return": round(row["avg_win"] or 0, 2),
                "avg_loss_return": round(row["avg_loss"] or 0, 2),
                "avg_confidence": round(row["avg_confidence"] or 0, 1),
                "period_days": days,
            }
        return {"total_predictions": 0, "accuracy": 0, "period_days": days}
    
    def get_signals_by_accuracy(self, lookback_days: int = 30) -> Dict:
        """Get signal accuracy breakdown by signal type."""
        cutoff = (datetime.utcnow() - timedelta(days=lookback_days)).isoformat()
        rows = self.db.execute_read(
            """
            SELECT signal, COUNT(*) as total, SUM(was_correct) as correct
            FROM predictions 
            WHERE outcome IS NOT NULL AND predicted_at > ?
            GROUP BY signal
            """,
            (cutoff,),
        )
        result = {}
        for row in rows:
            result[row["signal"]] = {
                "total": row["total"],
                "correct": row["correct"] or 0,
                "accuracy": round((row["correct"] or 0) / row["total"] * 100, 1),
            }
        return result
    
    # ─── PATTERNS ────────────────────────────────────────────────
    
    def store_pattern(self, name: str, pattern_type: str, conditions: dict, confidence: float = 0.5):
        """Store or update a trading pattern."""
        self.db.execute(
            """
            INSERT OR REPLACE INTO patterns 
            (pattern_name, pattern_type, conditions, avg_confidence, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (name, pattern_type, json.dumps(conditions), confidence),
        )
    
    def _update_pattern_success(self, pattern_name: str, was_correct: int):
        """Update pattern success rate after a prediction is resolved."""
        self.db.execute(
            """
            UPDATE patterns 
            SET total_uses = total_uses + 1,
                successful_uses = successful_uses + ?,
                success_rate = CASE 
                    WHEN (total_uses + 1) > 0 
                    THEN (successful_uses + ?) * 100.0 / (total_uses + 1)
                    ELSE 0 
                END,
                updated_at = CURRENT_TIMESTAMP
            WHERE pattern_name = ?
            """,
            (was_correct, was_correct, pattern_name),
        )
    
    def get_top_patterns(self, min_uses: int = 5) -> List[Dict]:
        rows = self.db.execute_read(
            """
            SELECT * FROM patterns 
            WHERE total_uses >= ?
            ORDER BY success_rate DESC, total_uses DESC
            LIMIT 20
            """,
            (min_uses,),
        )
        return [dict(r) for r in rows]
    
    # ─── LEARNING RULES ──────────────────────────────────────────
    
    def store_learning_rule(self, name: str, rule_type: str, rule_data: dict, weight: float = 1.0):
        """Store a self-learned rule."""
        self.db.execute(
            """
            INSERT OR REPLACE INTO learning_rules 
            (rule_name, rule_type, rule_data, weight, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (name, rule_type, json.dumps(rule_data), weight),
        )
    
    def update_rule_performance(self, rule_name: str, success: bool):
        """Update rule performance metrics."""
        if success:
            self.db.execute(
                """
                UPDATE learning_rules 
                SET success_count = success_count + 1,
                    confidence_score = MIN(1.0, confidence_score + 0.05),
                    updated_at = CURRENT_TIMESTAMP
                WHERE rule_name = ?
                """,
                (rule_name,),
            )
        else:
            self.db.execute(
                """
                UPDATE learning_rules 
                SET failure_count = failure_count + 1,
                    confidence_score = MAX(0.0, confidence_score - 0.05),
                    updated_at = CURRENT_TIMESTAMP
                WHERE rule_name = ?
                """,
                (rule_name,),
            )
            # Deactivate failing rules
            self.db.execute(
                "UPDATE learning_rules SET active = 0 WHERE confidence_score < 0.2 AND rule_name = ?",
                (rule_name,),
            )
    
    def get_active_rules(self) -> List[Dict]:
        rows = self.db.execute_read(
            "SELECT * FROM learning_rules WHERE active = 1 ORDER BY confidence_score DESC"
        )
        return [dict(r) for r in rows]
    
    # ─── MARKET CONTEXT ──────────────────────────────────────────
    
    def store_market_context(
        self, date: str, nifty_value: float = None,
        bank_nifty_value: float = None, sentiment: str = None,
        volatility: float = None,
    ):
        self.db.execute(
            """
            INSERT OR REPLACE INTO market_context 
            (date, nifty_value, bank_nifty_value, market_sentiment, volatility)
            VALUES (?, ?, ?, ?, ?)
            """,
            (date, nifty_value, bank_nifty_value, sentiment, volatility),
        )
    
    # ─── STRATEGY PERFORMANCE ────────────────────────────────────
    
    def store_backtest_result(self, strategy_name: str, symbol: str,
                              start_date: str, end_date: str, metrics: Dict):
        """Store backtest results."""
        self.db.execute_insert(
            """
            INSERT INTO strategy_performance
            (strategy_name, symbol, period_start, period_end, total_trades,
             winning_trades, losing_trades, win_rate, avg_profit, avg_loss,
             profit_factor, sharpe_ratio, max_drawdown)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                strategy_name, symbol, start_date, end_date,
                metrics.get("total_trades", 0),
                metrics.get("winning_trades", 0),
                metrics.get("losing_trades", 0),
                metrics.get("win_rate", 0),
                metrics.get("avg_profit", 0),
                metrics.get("avg_loss", 0),
                metrics.get("profit_factor", 0),
                metrics.get("sharpe_ratio", 0),
                metrics.get("max_drawdown", 0),
            ),
        )
    
    # ─── STATS ───────────────────────────────────────────────────
    
    def get_stats(self) -> Dict:
        """Get overall brain statistics."""
        stats = {}
        
        rows = self.db.execute_read("SELECT COUNT(*) as cnt FROM predictions")
        stats["total_predictions"] = rows[0]["cnt"]
        
        rows = self.db.execute_read("SELECT COUNT(*) as cnt FROM predictions WHERE outcome IS NOT NULL")
        stats["resolved_predictions"] = rows[0]["cnt"]
        
        rows = self.db.execute_read("SELECT COUNT(*) as cnt FROM patterns")
        stats["total_patterns"] = rows[0]["cnt"]
        
        rows = self.db.execute_read("SELECT COUNT(*) as cnt FROM learning_rules WHERE active = 1")
        stats["active_rules"] = rows[0]["cnt"]
        
        rows = self.db.execute_read(
            "SELECT SUM(was_correct) * 100.0 / COUNT(*) as acc FROM predictions WHERE outcome IS NOT NULL"
        )
        stats["overall_accuracy"] = round(rows[0]["acc"], 1) if rows and rows[0]["acc"] else 0
        
        return stats
    
    def close(self):
        """Don't actually close — the DatabaseManager manages the lifecycle."""
        pass  # DB is managed centrally
