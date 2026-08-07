"""
Tests for AI Trader v2.0
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import asyncio
from datetime import datetime


# Test imports
def test_config_import():
    from config import settings
    assert settings.app_name == "AI Trader"
    assert settings.port == 8000

def test_models_import():
    from models.stock import StockInfo, TradingSignal, SignalType, NIFTY_50_SYMBOLS
    assert len(NIFTY_50_SYMBOLS) > 0
    assert SignalType.BUY.value == "BUY"

def test_indicators():
    import pandas as pd
    import numpy as np
    from services.indicators import indicators
    
    # Create test data
    dates = pd.date_range('2024-01-01', periods=100)
    df = pd.DataFrame({
        'Open': np.random.uniform(100, 200, 100),
        'High': np.random.uniform(150, 250, 100),
        'Low': np.random.uniform(50, 150, 100),
        'Close': np.random.uniform(100, 200, 100),
        'Volume': np.random.uniform(1000000, 5000000, 100),
    }, index=dates)
    
    # Make sure High > Close > Low
    df['High'] = df[['Open', 'Close', 'High']].max(axis=1)
    df['Low'] = df[['Open', 'Close', 'Low']].min(axis=1)
    
    result = indicators.calculate_all(df)
    assert result is not None
    assert result.rsi is not None or len(df) < 15  # RSI needs 14+ periods
    assert result.sma_20 is not None

def test_advanced_indicators():
    import pandas as pd
    import numpy as np
    from services.advanced_indicators import advanced_indicators
    
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
    assert 'pivot_points' in result

def test_brain():
    from ai_agent.brain import ArthBrain
    brain = ArthBrain("test_brain.db")
    
    # Store a prediction
    pred_id = brain.store_prediction("TEST", "BUY", 75, 100.0, 105.0, 98.0)
    assert pred_id is not None
    
    # Get stats
    stats = brain.get_stats()
    assert stats['total_predictions'] >= 1
    
    # Store a pattern
    brain.store_pattern("test_pattern", "bullish", {"test": True})
    
    # Get patterns
    patterns = brain.get_top_patterns(min_uses=0)
    assert len(patterns) >= 1
    
    # Clean up
    brain.close()
    os.remove("test_brain.db")

def test_pattern_detection():
    import pandas as pd
    import numpy as np
    from ai_agent.analyzer import ArthAnalyzer
    
    analyzer = ArthAnalyzer()
    
    # Create test data with a hammer-like pattern
    dates = pd.date_range('2024-01-01', periods=10)
    df = pd.DataFrame({
        'Open': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
        'High': [105, 106, 107, 108, 109, 110, 111, 112, 113, 112],
        'Low': [98, 99, 100, 101, 102, 103, 104, 105, 100, 105],
        'Close': [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
        'Volume': [1000000] * 10,
    }, index=dates)
    
    patterns = analyzer.detect_patterns(df)
    # Should detect some patterns (or none if data doesn't match)
    assert isinstance(patterns, list)

def test_fibonacci():
    from services.advanced_indicators import advanced_indicators
    
    levels = advanced_indicators.calculate_fibonacci_levels(200, 100)
    assert levels['0.0'] == 200
    assert levels['100.0'] == 100
    assert levels['50.0'] == 150

def test_pivot_points():
    from services.advanced_indicators import advanced_indicators
    
    pivots = advanced_indicators.calculate_pivot_points(110, 90, 100)
    assert pivots['pivot'] == 100.0
    assert pivots['r1'] > pivots['pivot']
    assert pivots['s1'] < pivots['pivot']

def test_paper_trader():
    from services.paper_trader import PaperTrader
    
    trader = PaperTrader("test_paper.db")
    
    # Open a position
    result = trader.open_position("TEST", "BUY", 100.0, confidence=80)
    assert 'status' in result
    assert result['status'] == 'opened'
    
    # Get portfolio
    portfolio = trader.get_portfolio()
    assert portfolio['open_positions'] >= 1
    
    # Close position
    positions = [p for p in portfolio['positions'] if p['status'] == 'OPEN']
    if positions:
        close_result = trader.close_position(positions[0]['id'], 105.0)
        assert close_result['status'] == 'closed'
    
    # Clean up
    trader.close()
    os.remove("test_paper.db")

def test_app_routes():
    from main import app
    
    routes = [r.path for r in app.routes if hasattr(r, 'path')]
    
    # Check critical routes exist
    assert '/api/health' in routes
    assert '/' in routes
    
    # Check ARTH routes
    arth_routes = [r for r in routes if '/arth/' in r]
    assert len(arth_routes) >= 5
    
    # Check backtest routes
    bt_routes = [r for r in routes if '/backtest/' in r]
    assert len(bt_routes) >= 3
    
    # Check paper trading routes
    paper_routes = [r for r in routes if '/paper/' in r]
    assert len(paper_routes) >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
