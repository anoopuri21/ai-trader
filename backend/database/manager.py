"""
Database Manager — Single source of truth for all database connections.

Architecture Fix: Previously, brain.py, paper_trader.py, and backtest.py each
created their own SQLite connections with relative paths. This caused:
  1. Data written to one file but read from another
  2. Different working directories creating orphan databases
  3. No connection pooling or thread safety

Now: One DatabaseManager creates all connections to a single .db file
with proper thread safety via a threading lock for writes.
"""

import sqlite3
import json
import logging
import threading
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Fixed database path — always relative to the backend directory, NOT cwd
DB_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DB_DIR / "ai_trader.db"


class DatabaseManager:
    """
    Central database manager.
    
    All database access goes through this singleton.
    Uses a single SQLite file with thread-safe writes.
    """
    
    _instance: Optional['DatabaseManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """True singleton — only one instance ever."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, db_path: Optional[str] = None):
        # Only initialize once
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._write_lock = threading.Lock()
        self._db_path = Path(db_path) if db_path else DB_PATH
        
        # Ensure directory exists
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create connection with proper settings
        self._conn = sqlite3.connect(
            str(self._db_path),
            check_same_thread=False,
            isolation_level=None,  # Manual transaction control
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent reads
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA cache_size=1000")
        
        self._init_tables()
        self._initialized = True
        logger.info(f"DatabaseManager initialized: {self._db_path}")
    
    @property
    def conn(self) -> sqlite3.Connection:
        return self._conn
    
    @property
    def db_path(self) -> Path:
        return self._db_path
    
    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Thread-safe write operation."""
        with self._write_lock:
            cursor = self._conn.cursor()
            cursor.execute(sql, params)
            return cursor
    
    def execute_read(self, sql: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Read operation (no lock needed with WAL mode)."""
        cursor = self._conn.cursor()
        cursor.execute(sql, params)
        return cursor.fetchall()
    
    def execute_insert(self, sql: str, params: tuple = ()) -> int:
        """Insert and return lastrowid. Thread-safe."""
        with self._write_lock:
            cursor = self._conn.cursor()
            cursor.execute(sql, params)
            return cursor.lastrowid
    
    def _init_tables(self):
        """Create all tables in a single database."""
        with self._write_lock:
            cursor = self._conn.cursor()
            
            # ─── ARTH BRAIN TABLES ───
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_name TEXT NOT NULL,
                    pattern_type TEXT NOT NULL,
                    conditions TEXT NOT NULL DEFAULT '{}',
                    success_rate REAL DEFAULT 0.0,
                    total_uses INTEGER DEFAULT 0,
                    successful_uses INTEGER DEFAULT 0,
                    avg_confidence REAL DEFAULT 0.0,
                    last_used TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
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
                    timeframe TEXT DEFAULT 'SWING',
                    predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    outcome TEXT,
                    actual_return REAL,
                    was_correct INTEGER,
                    resolved_at TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS learning_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_name TEXT NOT NULL UNIQUE,
                    rule_type TEXT NOT NULL,
                    rule_data TEXT NOT NULL DEFAULT '{}',
                    weight REAL DEFAULT 1.0,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    confidence_score REAL DEFAULT 0.5,
                    active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
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
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategy_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_name TEXT NOT NULL,
                    symbol TEXT,
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
            
            # ─── PAPER TRADING TABLES ───
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_portfolio (
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
                CREATE TABLE IF NOT EXISTS paper_positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    type TEXT NOT NULL,
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
                CREATE TABLE IF NOT EXISTS paper_trades (
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
            
            # Initialize paper portfolio if empty
            cursor.execute("SELECT COUNT(*) FROM paper_portfolio")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO paper_portfolio (initial_capital, current_cash, total_value)
                    VALUES (100000.0, 100000.0, 100000.0)
                """)
            
            self._conn.commit()
        
        logger.info("All database tables initialized")
    
    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
        DatabaseManager._instance = None
        self._initialized = False


def get_db() -> DatabaseManager:
    """Get the singleton DatabaseManager instance."""
    return DatabaseManager()


def get_db_path() -> Path:
    """Get the database file path (useful for diagnostics)."""
    return DB_PATH
