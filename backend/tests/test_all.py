"""
Tests for AI Trader v2.0

Updated for new architecture:
  - Centralized DatabaseManager (no separate DB files)
  - ATR-based indicators
  - Contextual RSI analysis
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pandas as pd
import numpy as np
from datetime import datetime


def test_config_import():
    from config import settings, is_market_open
    assert settings.app_name == "AI Trader"
    assert settings.port == 8000
    assert isinstance(is_market_open(), bool)

def test_models_import():
    from models.stock import StockInfo, TradingSignal, SignalType, NIFTY_50_SYMBOLS
    assert len(NIFTY_50_SYMBOLS) > 0
    assert SignalType.BUY.value == "BUY"

def test_database_manager():
    """Test centralized database manager."""
    from database.manager import DatabaseManager, get_db, get_db_path
    
    db1 = get_db()
    db2 = get_db()
    assert db1 is db2, "DatabaseManager should be singleton"
    
    path = get_db_path()
    assert path.exists(), "Database file should exist"
    assert path.parent.name == "data", "DB should be in data/ directory"

def test_indicators():
    from services.indicators import indicators
    
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=100)
    df = pd.DataFrame({
        'Open': np.random.uniform(100, 200, 100),
        'High': np.random.uniform(150, 250, 100),
        'Low': np.random.uniform(50, 150, 100),
        'Close': np.random.uniform(100, 200, 100),
        'Volume': np.random.uniform(1000000, 5000000, 100),
    }, index=dates)
    df['High'] = df[['Open', 'Close', 'High']].max(axis=1)
    df['Low'] = df[['Open', 'Close', 'Low']].min(axis=1)
    
    result = indicators.calculate_all(df)
    assert result is not None
    assert result.atr is not None, "ATR should be calculated"
    assert result.atr > 0, "ATR should be positive"

def test_advanced_indicators():
    from services.advanced_indicators import advanced_indicators
    
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=100)
    df = pd.DataFrame({
        'Open': np.random.uniform(100, 200, 100),
        'High': np.random.uniform(150, 250, 100),
        'Low': np.random.uniform(50, 150, 100),
        'Close': np.random.uniform(100, 200, 100),
        'Volume': np.random.uniform(1000000, 5000000, 100),
    }, index=dates)
    df['High'] = df[['Open', 'Close', 'High']].max(axis=1)
    df['Low'] = df[['Open', 'Close', 'Low']].min(axis=1)
    
    result = advanced_indicators.get_all_advanced(df)
    assert 'bollinger' in result
    assert 'atr' in result
    assert 'fibonacci' in result

def test_brain():
    """Test ARTH brain using centralized database."""
    from ai_agent.brain import ArthBrain
    
    brain = ArthBrain()  # Uses centralized DB
    
    pred_id = brain.store_prediction("TEST", "BUY", 75, 100.0, 105.0, 98.0)
    assert pred_id is not None
    
    stats = brain.get_stats()
    assert stats['total_predictions'] >= 1
    
    brain.store_pattern("test_pattern", "bullish", {"test": True})
    patterns = brain.get_top_patterns(min_uses=0)
    assert len(patterns) >= 1

def test_pattern_detection():
    from ai_agent.analyzer import ArthAnalyzer
    
    analyzer = ArthAnalyzer()
    
    dates = pd.date_range('2024-01-01', periods=10)
    df = pd.DataFrame({
        'Open': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
        'High': [105, 106, 107, 108, 109, 110, 111, 112, 113, 112],
        'Low': [98, 99, 100, 101, 102, 103, 104, 105, 100, 105],
        'Close': [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
        'Volume': [1000000] * 10,
    }, index=dates)
    
    patterns = analyzer.detect_patterns(df)
    assert isinstance(patterns, list)

def test_signal_generator_scoring():
    """Test that signal generator uses proper scoring."""
    from services.signal_generator import SignalGenerator
    
    gen = SignalGenerator()
    
    # Test contextual RSI
    from models.stock import TrendType
    
    # In bullish trend, RSI 50 = momentum (bullish)
    score = gen._score_rsi_contextual(50, TrendType.BULLISH)
    assert score > 0, "RSI 50 in uptrend should be bullish"
    
    # In bearish trend, RSI 50 = momentum (bearish)
    score = gen._score_rsi_contextual(50, TrendType.BEARISH)
    assert score < 0, "RSI 50 in downtrend should be bearish"
    
    # In neutral, RSI < 30 = oversold (buy)
    score = gen._score_rsi_contextual(25, TrendType.NEUTRAL)
    assert score > 0, "RSI < 30 in neutral should be bullish"

def test_fibonacci():
    from services.advanced_indicators import advanced_indicators
    levels = advanced_indicators.calculate_fibonacci_levels(200, 100)
    assert levels['0.0'] == 200
    assert levels['100.0'] == 100
    assert levels['50.0'] == 150

def test_paper_trader():
    """Test paper trading using centralized database."""
    from services.paper_trader import PaperTrader
    
    trader = PaperTrader()  # Uses centralized DB
    
    result = trader.open_position("TEST", "BUY", 100.0, confidence=80)
    assert result['status'] == 'opened'
    
    portfolio = trader.get_portfolio()
    assert portfolio['open_positions'] >= 1
    
    positions = [p for p in portfolio['positions'] if p['status'] == 'OPEN']
    if positions:
        close_result = trader.close_position(positions[0]['id'], 105.0)
        assert close_result['status'] == 'closed'

def test_app_routes():
    from main import app
    routes = [r.path for r in app.routes if hasattr(r, 'path')]
    
    assert '/api/health' in routes
    
    arth_routes = [r for r in routes if '/arth/' in r]
    assert len(arth_routes) >= 5
    
    paper_routes = [r for r in routes if '/paper/' in r]
    assert len(paper_routes) >= 3

def test_market_hours():
    """Test market hours calculation."""
    from config import is_market_open
    result = is_market_open()
    assert isinstance(result, bool)

def test_transaction_costs():
    """Test backtest includes transaction costs."""
    from ai_agent.backtest import BacktestEngine
    engine = BacktestEngine()
    assert engine.total_cost > 0, "Transaction cost should be positive"
    assert engine.total_cost < 0.01, "Cost should be reasonable"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
