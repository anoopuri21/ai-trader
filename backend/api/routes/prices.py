"""
AI Trader - Prices API Routes
Phase 1: Price data endpoints
"""

import re
from typing import Optional
from fastapi import APIRouter, Query, Request, HTTPException
from datetime import datetime

from models.stock import StockInfo
from services.price_fetcher import price_fetcher, NIFTY_50_SYMBOLS, NIFTY_BANK_SYMBOLS
from middleware.rate_limit import check_rate_limit

_SYMBOL_RE = re.compile(r"^[A-Z0-9]{1,12}$")

router = APIRouter(prefix="/api/prices", tags=["Prices"])


@router.get("/")
async def get_all_prices(
    index: Optional[str] = Query(None, description="Filter: nifty50, niftybank, all")
):
    """
    Get current prices for all tracked stocks.
    - **index**: Filter by 'nifty50', 'niftybank', or 'all'
    """
    if index == "nifty50":
        symbols = NIFTY_50_SYMBOLS
    elif index == "niftybank":
        symbols = NIFTY_BANK_SYMBOLS
    else:
        symbols = list(set(NIFTY_50_SYMBOLS + NIFTY_BANK_SYMBOLS))
    
    prices = await price_fetcher.get_prices(symbols)
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "count": len(prices),
        "prices": prices
    }


@router.get("/{symbol}")
async def get_price(symbol: str, request: Request):
    """
    Get current price for a specific stock.
    """
    await check_rate_limit(request, "global")
    sym = symbol.strip().upper().replace(".NS","")
    if not _SYMBOL_RE.match(sym):
        raise HTTPException(status_code=422, detail="Invalid symbol")
    symbol = sym
    price = await price_fetcher.get_price(symbol)
    
    if not price:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Price not found for: {symbol}")
    
    return price


@router.get("/batch/list")
async def get_prices_list(
    symbols: str = Query(..., description="Comma-separated symbols (max 20)"),
    request: Request = None,
):
    """
    Get prices for multiple specific symbols.
    """
    if request:
        await check_rate_limit(request, "global")
    # Clamp + validate
    raw = symbols.split(",")[:20]
    symbol_list = []
    for s in raw:
        sym = s.strip().upper().replace(".NS","")
        if _SYMBOL_RE.match(sym):
            symbol_list.append(sym)
    if not symbol_list:
        raise HTTPException(status_code=422, detail="No valid symbols")
    prices = await price_fetcher.get_prices(symbol_list)
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "requested": len(symbol_list),
        "found": len(prices),
        "prices": prices
    }


@router.get("/indices/summary")
async def get_indices():
    """
    Get Nifty 50 and Nifty Bank index summary.
    """
    indices = await price_fetcher.get_index_data()
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "indices": indices
    }


@router.get("/indices/nifty50")
async def get_nifty50():
    """Get all Nifty 50 stocks"""
    prices = await price_fetcher.get_prices(NIFTY_50_SYMBOLS)
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "index": "Nifty 50",
        "count": len(prices),
        "stocks": prices
    }


@router.get("/indices/niftybank")
async def get_niftybank():
    """Get all Nifty Bank stocks"""
    prices = await price_fetcher.get_prices(NIFTY_BANK_SYMBOLS)
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "index": "Nifty Bank",
        "count": len(prices),
        "stocks": prices
    }
