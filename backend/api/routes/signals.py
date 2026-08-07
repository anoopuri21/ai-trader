"""
AI Trader - Signals API Routes
Phase 1: Trading signal endpoints
"""

from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from datetime import datetime

from models.stock import SignalsResponse, SignalType
from services.signal_generator import signal_generator

router = APIRouter(prefix="/api/signals", tags=["Signals"])


@router.get("/", response_model=SignalsResponse)
async def get_all_signals(
    index: Optional[str] = Query("all", description="Filter: nifty50, niftybank, all"),
    signal_type: Optional[str] = Query(None, description="Filter: BUY, SELL, HOLD")
):
    """
    Get trading signals for all stocks.
    """
    signals = await signal_generator.generate_all_signals(index=index)
    
    # Apply filter if specified
    if signal_type:
        try:
            sig = SignalType(signal_type.upper())
            signals.signals = [s for s in signals.signals if s.signal == sig]
            signals.count = len(signals.signals)
        except ValueError:
            pass
    
    return signals


@router.get("/{symbol}")
async def get_signal(symbol: str):
    """
    Get detailed signal for a specific stock.
    """
    symbol = symbol.upper()
    signal = await signal_generator.generate_signal(symbol)
    
    if not signal:
        raise HTTPException(status_code=404, detail=f"No signal for: {symbol}")
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "symbol": symbol,
        "signal": signal
    }


@router.get("/summary/overview")
async def get_overview():
    """
    Get quick signal overview with counts.
    """
    signals = await signal_generator.generate_all_signals()
    
    # Top buy/sell by confidence
    buy_signals = sorted(
        [s for s in signals.signals if s.signal == SignalType.BUY],
        key=lambda x: x.confidence,
        reverse=True
    )[:5]
    
    sell_signals = sorted(
        [s for s in signals.signals if s.signal == SignalType.SELL],
        key=lambda x: x.confidence,
        reverse=True
    )[:5]
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "summary": {
            "total": signals.count,
            "buy": signals.buy_count,
            "sell": signals.sell_count,
            "hold": signals.hold_count,
            "buy_pct": round(signals.buy_count / signals.count * 100, 1) if signals.count > 0 else 0,
            "sell_pct": round(signals.sell_count / signals.count * 100, 1) if signals.count > 0 else 0
        },
        "top_buy": [
            {"symbol": s.stock.symbol, "name": s.stock.name, "price": s.stock.current_price,
             "change": s.stock.change_percent, "confidence": s.confidence}
            for s in buy_signals
        ],
        "top_sell": [
            {"symbol": s.stock.symbol, "name": s.stock.name, "price": s.stock.current_price,
             "change": s.stock.change_percent, "confidence": s.confidence}
            for s in sell_signals
        ]
    }


@router.get("/trending/bullish")
async def get_bullish(limit: int = Query(10, ge=1, le=50)):
    """Get top BUY signals by confidence"""
    signals = await signal_generator.generate_all_signals()
    
    bullish = sorted(
        [s for s in signals.signals if s.signal == SignalType.BUY],
        key=lambda x: (x.confidence, s.stock.change_percent),
        reverse=True
    )[:limit]
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "count": len(bullish),
        "signals": bullish
    }


@router.get("/trending/bearish")
async def get_bearish(limit: int = Query(10, ge=1, le=50)):
    """Get top SELL signals by confidence"""
    signals = await signal_generator.generate_all_signals()
    
    bearish = sorted(
        [s for s in signals.signals if s.signal == SignalType.SELL],
        key=lambda x: (x.confidence, -s.stock.change_percent),
        reverse=True
    )[:limit]
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "count": len(bearish),
        "signals": bearish
    }
