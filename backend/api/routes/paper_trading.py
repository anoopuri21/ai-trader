"""
Paper Trading API Routes
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from services.paper_trader import paper_trader
from services.price_fetcher import price_fetcher

router = APIRouter(prefix="/api/paper", tags=["Paper Trading"])


class OpenPositionRequest(BaseModel):
    symbol: str
    signal: str  # BUY or SELL
    allocation_pct: float = 0.1


class ClosePositionRequest(BaseModel):
    position_id: int


@router.get("/portfolio")
async def get_portfolio():
    """Get current paper trading portfolio"""
    return paper_trader.get_portfolio()


@router.post("/open")
async def open_position(request: OpenPositionRequest):
    """Open a new paper position"""
    symbol = request.symbol.upper()
    
    # Get current price
    stock = await price_fetcher.get_price(symbol)
    if not stock:
        raise HTTPException(status_code=404, detail=f"Cannot find price for {symbol}")
    
    result = paper_trader.open_position(
        symbol=symbol,
        signal=request.signal,
        price=stock.current_price,
        allocation_pct=request.allocation_pct,
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/close/{position_id}")
async def close_position(position_id: int):
    """Close an open paper position"""
    cursor = paper_trader.conn.cursor()
    cursor.execute("SELECT * FROM positions WHERE id = ? AND status = 'OPEN'", (position_id,))
    pos = cursor.fetchone()
    
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")
    
    # Get current price
    stock = await price_fetcher.get_price(pos['symbol'])
    if not stock:
        raise HTTPException(status_code=500, detail="Cannot fetch current price")
    
    result = paper_trader.close_position(position_id, stock.current_price, "manual_close")
    return result


@router.get("/positions")
async def get_positions():
    """Get all open positions"""
    portfolio = paper_trader.get_portfolio()
    return {
        "open_positions": portfolio['positions'],
        "count": len(portfolio['positions']),
    }


@router.get("/trades")
async def get_trades(limit: int = Query(50, ge=1, le=200)):
    """Get trade history"""
    trades = paper_trader.get_trade_history(limit)
    return {
        "count": len(trades),
        "trades": trades,
    }


@router.get("/performance")
async def get_performance():
    """Get paper trading performance"""
    return paper_trader.get_performance()


@router.post("/auto-trade/{symbol}")
async def auto_trade(symbol: str):
    """
    Auto-trade based on ARTH's signal for a symbol.
    Analyzes the stock and opens a paper position if signal is strong.
    """
    from ai_agent.arth import arth
    
    analysis = await arth.analyze_stock(symbol.upper())
    if "error" in analysis:
        raise HTTPException(status_code=404, detail=analysis["error"])
    
    signal = analysis['signal']
    confidence = analysis['confidence']
    
    if signal == "HOLD" or confidence < 60:
        return {
            "action": "SKIP",
            "reason": f"Signal is {signal} with {confidence}% confidence (need ≥60%)",
            "analysis": {
                "signal": signal,
                "confidence": confidence,
            }
        }
    
    # Open position
    result = paper_trader.open_position(
        symbol=symbol.upper(),
        signal=signal,
        price=analysis['price']['current'],
        confidence=confidence,
        stop_loss=analysis['levels'].get('stop_loss'),
        target=analysis['levels'].get('target'),
        allocation_pct=0.1 if confidence < 80 else 0.15,
    )
    
    return {
        "action": "TRADED",
        "signal": signal,
        "confidence": confidence,
        "trade": result,
    }
