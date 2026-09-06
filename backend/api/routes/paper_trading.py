"""
Paper Trading API Routes
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Request
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import datetime
import re

from services.paper_trader import paper_trader
from services.price_fetcher import price_fetcher
from api.deps import verify_api_key_optional
from middleware.rate_limit import check_rate_limit

_SYMBOL_RE = re.compile(r"^[A-Z0-9]{1,12}$")

router = APIRouter(prefix="/api/paper", tags=["Paper Trading"])


class OpenPositionRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=12, description="NSE symbol e.g. RELIANCE")
    signal: Literal["BUY", "SELL"]
    allocation_pct: float = Field(0.1, ge=0.001, le=0.5, description="0.001..0.5 (0.1=10%)")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        s = v.strip().upper().replace(".NS", "")
        if not _SYMBOL_RE.match(s):
            raise ValueError("Invalid symbol")
        return s


class ClosePositionRequest(BaseModel):
    position_id: int


@router.get("/portfolio")
async def get_portfolio():
    """Get current paper trading portfolio"""
    return paper_trader.get_portfolio()


@router.post("/open")
async def open_position(request: Request, body: OpenPositionRequest, _auth=Depends(verify_api_key_optional)):
    """Open a new paper position — rate limited 60/min, auth optional if ARTH_API_KEY set"""
    await check_rate_limit(request, "global")
    symbol = body.symbol.upper()
    
    # Get current price
    stock = await price_fetcher.get_price(symbol)
    if not stock:
        raise HTTPException(status_code=404, detail=f"Cannot find price for {symbol}")
    
    result = paper_trader.open_position(
        symbol=symbol,
        signal=body.signal,
        price=stock.current_price,
        allocation_pct=body.allocation_pct,
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/close/{position_id}")
async def close_position(position_id: int, request: Request, _auth=Depends(verify_api_key_optional)):
    """Close an open paper position"""
    await check_rate_limit(request, "global")
    if position_id <= 0 or position_id > 1_000_000:
        raise HTTPException(status_code=422, detail="Invalid position_id")
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
async def auto_trade(symbol: str, request: Request, _auth=Depends(verify_api_key_optional)):
    """
    Auto-trade based on ARTH's signal for a symbol.
    Analyzes the stock and opens a paper position if signal is strong.
    """
    await check_rate_limit(request, "strict")
    import re as _re
    if not _re.match(r"^[A-Z0-9]{1,12}$", symbol.strip().upper().replace(".NS","")):
        raise HTTPException(status_code=422, detail="Invalid symbol")
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
