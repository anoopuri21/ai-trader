"""
AI Trader - Backtesting API Routes
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime

from ai_agent.backtest import backtest_engine
from ai_agent.arth import arth

router = APIRouter(prefix="/api/backtest", tags=["Backtesting"])


@router.get("/run")
async def run_backtest(
    symbol: str = Query(..., description="Stock symbol (e.g., RELIANCE)"),
    strategy: str = Query("rule_based", description="Strategy: rule_based, momentum, mean_reversion, combined"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    initial_capital: float = Query(100000.0, description="Initial capital"),
):
    """
    Run backtest for a symbol with given strategy.
    Returns performance metrics and trade history.
    """
    result = await backtest_engine.run_backtest(
        symbol=symbol.upper(),
        strategy=strategy,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/compare")
async def compare_strategies(
    symbol: str = Query(..., description="Stock symbol"),
):
    """
    Compare all strategies for a symbol.
    """
    strategies = ["rule_based", "momentum", "mean_reversion", "combined"]
    results = {}
    
    for strategy in strategies:
        result = await backtest_engine.run_backtest(
            symbol=symbol.upper(),
            strategy=strategy,
        )
        if "error" not in result:
            results[strategy] = result["metrics"]
    
    # Find best strategy
    if results:
        best = max(results.items(), key=lambda x: x[1].get('total_return', 0))
        return {
            "symbol": symbol.upper(),
            "strategies": results,
            "best_strategy": best[0],
            "best_return": best[1].get('total_return', 0),
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    return {"error": "No results available"}


@router.get("/performance")
async def get_performance():
    """
    Get all stored strategy performance data.
    """
    if not arth.brain:
        raise HTTPException(status_code=503, detail="ARTH not initialized")
    
    cursor = arth.brain.conn.cursor()
    cursor.execute("""
        SELECT * FROM strategy_performance 
        ORDER BY created_at DESC LIMIT 50
    """)
    
    rows = [dict(row) for row in cursor.fetchall()]
    return {
        "count": len(rows),
        "strategies": rows,
    }


@router.get("/accuracy")
async def get_accuracy(
    days: int = Query(30, ge=1, le=365),
):
    """
    Get ARTH's prediction accuracy breakdown.
    """
    if not arth.brain:
        raise HTTPException(status_code=503, detail="ARTH not initialized")
    
    accuracy = arth.brain.get_prediction_accuracy(days)
    signals_breakdown = arth.brain.get_signals_by_accuracy(days)
    
    return {
        "period_days": days,
        "overall": accuracy,
        "by_signal_type": signals_breakdown,
        "timestamp": datetime.utcnow().isoformat(),
    }
