"""
ARTH's Brain - Central Knowledge Base
All learning is stored here - patterns, predictions, success rates
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class ArthBrain:
    """
    ARTH's central brain using SQLite for knowledge storage.
    Stores patterns, predictions, and learns from outcomes.
    """
    
    def __init__(self, db_path: str = "arth_brain.db"):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        
        # Patterns table - learned trading patterns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_name TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                conditions TEXT NOT NULL,
                success_rate REAL DEFAULT 0.0,
                total_uses INTEGER DEFAULT 0,
                successful_uses INTEGER DEFAULT 0,
                avg_confidence REAL DEFAULT 0.0,
                last_used TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Predictions table - track every prediction
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                signal TEXT NOT NULL,
                confidence INTEGER NOT NULL,
                entry_price REAL,
                target_price REAL,
                stop_loss REAL,
                indicators_snapshot TEXT,
                ai_provider TEXT,
                ai_reasoning TEXT,
                pattern_used TEXT,
                predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                outcome TEXT,
                actual_return REAL,
                was_correct INTEGER,
                resolved_at TIMESTAMP
            )
        """)
        
        # Learning rules - ARTH's self-improvement rules
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_name TEXT NOT NULL UNIQUE,
                rule_type TEXT NOT NULL,
                rule_data TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                confidence_score REAL DEFAULT 0.5,
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Market context - store market conditions with predictions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                nifty_value REAL,
                bank_nifty_value REAL,
                market_sentiment TEXT,
                volatility REAL,
                fear_greed_index REAL,
                sector_rotation TEXT,
                notes TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Strategy performance - track overall strategy results
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0.0,
                avg_profit REAL DEFAULT 0.0,
                avg_loss REAL DEFAULT 0.0,
                profit_factor REAL DEFAULT 0.0,
                sharpe_ratio REAL DEFAULT 0.0,
                max_drawdown REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.commit()
        logger.info("ARTH's brain initialized with knowledge tables")
    
    def store_prediction(self, symbol: str, signal: str, confidence: int,
                        entry_price: float = None, target_price: float = None,
                        stop_loss: float = None, indicators: dict = None,
                        ai_provider: str = None, ai_reasoning: str = None,
                        pattern_used: str = None) -> int:
        """Store a new prediction"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO predictions 
            (symbol, signal, confidence, entry_price, target_price, stop_loss,
             indicators_snapshot, ai_provider, ai_reasoning, pattern_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            symbol, signal, confidence, entry_price, target_price, stop_loss,
            json.dumps(indicators) if indicators else None,
            ai_provider, ai_reasoning, pattern_used
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def resolve_prediction(self, prediction_id: int, outcome: str, actual_return: float):
        """Resolve a prediction with actual outcome"""
        cursor = self.conn.cursor()
        was_correct = 1 if outcome in ["WIN", "PROFIT"] else 0
        cursor.execute("""
            UPDATE predictions 
            SET outcome = ?, actual_return = ?, was_correct = ?, resolved_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (outcome, actual_return, was_correct, prediction_id))
        self.conn.commit()
        
        # Update pattern success rate if pattern was used
        cursor.execute("SELECT pattern_used FROM predictions WHERE id = ?", (prediction_id,))
        row = cursor.fetchone()
        if row and row['pattern_used']:
            self._update_pattern_success(row['pattern_used'], was_correct)
    
    def store_pattern(self, name: str, pattern_type: str, conditions: dict, 
                     confidence: float = 0.5):
        """Store or update a trading pattern"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO patterns 
            (pattern_name, pattern_type, conditions, avg_confidence, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (name, pattern_type, json.dumps(conditions), confidence))
        self.conn.commit()
    
    def _update_pattern_success(self, pattern_name: str, was_correct: int):
        """Update pattern success rate"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE patterns 
            SET total_uses = total_uses + 1,
                successful_uses = successful_uses + ?,
                success_rate = (successful_uses + ?) * 100.0 / (total_uses + 1),
                updated_at = CURRENT_TIMESTAMP
            WHERE pattern_name = ?
        """, (was_correct, was_correct, pattern_name))
        self.conn.commit()
    
    def store_learning_rule(self, name: str, rule_type: str, rule_data: dict, weight: float = 1.0):
        """Store a self-learned rule"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO learning_rules 
            (rule_name, rule_type, rule_data, weight, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (name, rule_type, json.dumps(rule_data), weight))
        self.conn.commit()
    
    def update_rule_performance(self, rule_name: str, success: bool):
        """Update rule performance metrics"""
        cursor = self.conn.cursor()
        if success:
            cursor.execute("""
                UPDATE learning_rules 
                SET success_count = success_count + 1,
                    confidence_score = MIN(1.0, confidence_score + 0.05),
                    updated_at = CURRENT_TIMESTAMP
                WHERE rule_name = ?
            """, (rule_name,))
        else:
            cursor.execute("""
                UPDATE learning_rules 
                SET failure_count = failure_count + 1,
                    confidence_score = MAX(0.0, confidence_score - 0.05),
                    updated_at = CURRENT_TIMESTAMP
                WHERE rule_name = ?
            """, (rule_name,))
        
        # Deactivate rules with very low confidence
        cursor.execute("""
            UPDATE learning_rules SET active = 0 
            WHERE confidence_score < 0.2 AND rule_name = ?
        """, (rule_name,))
        self.conn.commit()
    
    def store_market_context(self, date: str, nifty_value: float = None,
                            bank_nifty_value: float = None, sentiment: str = None,
                            volatility: float = None):
        """Store market context for a date"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO market_context 
            (date, nifty_value, bank_nifty_value, market_sentiment, volatility)
            VALUES (?, ?, ?, ?, ?)
        """, (date, nifty_value, bank_nifty_value, sentiment, volatility))
        self.conn.commit()
    
    def get_unresolved_predictions(self, days_old: int = 1) -> List[Dict]:
        """Get predictions that haven't been resolved yet"""
        cursor = self.conn.cursor()
        cutoff = (datetime.utcnow() - timedelta(days=days_old)).isoformat()
        cursor.execute("""
            SELECT * FROM predictions 
            WHERE outcome IS NULL AND predicted_at < ?
            ORDER BY predicted_at DESC
        """, (cutoff,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_recent_predictions(self, limit: int = 50) -> List[Dict]:
        """Get recent predictions"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM predictions 
            ORDER BY predicted_at DESC LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_prediction_accuracy(self, days: int = 30) -> Dict:
        """Get prediction accuracy for last N days"""
        cursor = self.conn.cursor()
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(was_correct) as correct,
                AVG(CASE WHEN was_correct = 1 THEN actual_return ELSE NULL END) as avg_win,
                AVG(CASE WHEN was_correct = 0 THEN actual_return ELSE NULL END) as avg_loss,
                AVG(confidence) as avg_confidence
            FROM predictions 
            WHERE outcome IS NOT NULL AND predicted_at > ?
        """, (cutoff,))
        row = cursor.fetchone()
        if row and row['total'] and row['total'] > 0:
            return {
                "total_predictions": row['total'],
                "correct_predictions": row['correct'] or 0,
                "accuracy": round((row['correct'] or 0) / row['total'] * 100, 1),
                "avg_win_return": round(row['avg_win'] or 0, 2),
                "avg_loss_return": round(row['avg_loss'] or 0, 2),
                "avg_confidence": round(row['avg_confidence'] or 0, 1),
                "period_days": days
            }
        return {"total_predictions": 0, "accuracy": 0, "period_days": days}
    
    def get_top_patterns(self, min_uses: int = 5) -> List[Dict]:
        """Get best performing patterns"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM patterns 
            WHERE total_uses >= ?
            ORDER BY success_rate DESC, total_uses DESC
            LIMIT 20
        """, (min_uses,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_active_rules(self) -> List[Dict]:
        """Get all active learning rules"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM learning_rules 
            WHERE active = 1
            ORDER BY confidence_score DESC
        """)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict:
        """Get overall brain statistics"""
        cursor = self.conn.cursor()
        
        stats = {}
        
        cursor.execute("SELECT COUNT(*) as cnt FROM predictions")
        stats['total_predictions'] = cursor.fetchone()['cnt']
        
        cursor.execute("SELECT COUNT(*) as cnt FROM predictions WHERE outcome IS NOT NULL")
        stats['resolved_predictions'] = cursor.fetchone()['cnt']
        
        cursor.execute("SELECT COUNT(*) as cnt FROM patterns")
        stats['total_patterns'] = cursor.fetchone()['cnt']
        
        cursor.execute("SELECT COUNT(*) as cnt FROM learning_rules WHERE active = 1")
        stats['active_rules'] = cursor.fetchone()['cnt']
        
        cursor.execute("""
            SELECT SUM(was_correct) * 100.0 / COUNT(*) as acc
            FROM predictions WHERE outcome IS NOT NULL
        """)
        row = cursor.fetchone()
        stats['overall_accuracy'] = round(row['acc'], 1) if row and row['acc'] else 0
        
        return stats
    
    def get_signals_by_accuracy(self, lookback_days: int = 30) -> Dict:
        """Get signal accuracy breakdown by signal type"""
        cursor = self.conn.cursor()
        cutoff = (datetime.utcnow() - timedelta(days=lookback_days)).isoformat()
        cursor.execute("""
            SELECT signal,
                   COUNT(*) as total,
                   SUM(was_correct) as correct
            FROM predictions 
            WHERE outcome IS NOT NULL AND predicted_at > ?
            GROUP BY signal
        """, (cutoff,))
        result = {}
        for row in cursor.fetchall():
            result[row['signal']] = {
                'total': row['total'],
                'correct': row['correct'] or 0,
                'accuracy': round((row['correct'] or 0) / row['total'] * 100, 1)
            }
        return result
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


# Singleton
brain = ArthBrain()
