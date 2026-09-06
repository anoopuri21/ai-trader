"""
AI Trader - Advanced Analysis API Routes
"""

import re as _re
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request, Depends
from pydantic import BaseModel, Field
from datetime import datetime

from services.price_fetcher import price_fetcher
from services.advanced_indicators import advanced_indicators
from ai_agent.sentiment import sentiment_analyzer
from services.news_fetcher import news_fetcher
from services.fundamentals import fundamentals_engine
from services.math_engine import math_engine
from api.deps import verify_api_key_optional
from middleware.rate_limit import check_rate_limit

_SYMBOL_RE = _re.compile(r"^[A-Z0-9]{1,12}$")

router = APIRouter(prefix="/api/analysis", tags=["Advanced Analysis"])


@router.get("/advanced/{symbol}")
async def get_advanced_analysis(symbol: str, request: Request):
    """Get all advanced technical indicators for a stock"""
    await check_rate_limit(request, "global")
    if not _SYMBOL_RE.match(symbol.strip().upper().replace(".NS","")):
        raise HTTPException(status_code=422, detail="Invalid symbol")
    df = await price_fetcher.get_historical_data(symbol, period="6mo")
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")
    
    result = advanced_indicators.get_all_advanced(df)
    return {
        "symbol": symbol.upper(),
        "timestamp": datetime.utcnow().isoformat(),
        "indicators": result,
    }


@router.get("/sentiment/market")
async def get_market_sentiment():
    """Get overall market sentiment"""
    sentiment = await sentiment_analyzer.get_market_sentiment()
    return sentiment


@router.get("/sentiment/{symbol}")
async def get_stock_sentiment(symbol: str):
    """Get sentiment for a specific stock"""
    sentiment = await sentiment_analyzer.get_stock_sentiment(symbol.upper())
    return {
        "symbol": symbol.upper(),
        **sentiment,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/fibonacci/{symbol}")
async def get_fibonacci(symbol: str, request: Request):
    """Get Fibonacci retracement levels"""
    await check_rate_limit(request, "global")
    if not _SYMBOL_RE.match(symbol.strip().upper().replace(".NS","")):
        raise HTTPException(status_code=422, detail="Invalid symbol")
    df = await price_fetcher.get_historical_data(symbol, period="3mo")
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")
    
    high = float(df['High'].max())
    low = float(df['Low'].min())
    
    levels = advanced_indicators.calculate_fibonacci_levels(high, low)
    return {
        "symbol": symbol.upper(),
        "period_high": high,
        "period_low": low,
        "fibonacci_levels": levels,
    }


@router.get("/pivot/{symbol}")
async def get_pivot_points(symbol: str, request: Request):
    """Get pivot points for a stock"""
    await check_rate_limit(request, "global")
    if not _SYMBOL_RE.match(symbol.strip().upper().replace(".NS","")):
        raise HTTPException(status_code=422, detail="Invalid symbol")
    stock = await price_fetcher.get_price(symbol.upper())
    if not stock:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")
    
    pivots = advanced_indicators.calculate_pivot_points(stock.high, stock.low, stock.current_price)
    return {
        "symbol": symbol.upper(),
        "pivot_points": pivots,
        "current_price": stock.current_price,
    }


# ─── NEW 4 Engines — Phase 4 ────────────────────────────────────

@router.get("/news-market/all")
async def get_all_market_news(request: Request, limit: int = Query(10, ge=1, le=20)):
    await check_rate_limit(request, "global")
    news = await news_fetcher.get_market_news(limit=limit)
    sentiment = await news_fetcher.get_market_sentiment()
    return {"news": news, "sentiment": sentiment, "timestamp": datetime.utcnow().isoformat()}


@router.get("/news/{symbol}")
async def get_news(symbol: str, request: Request, limit: int = Query(8, ge=1, le=20)):
    """Market news & sentiment (Engine #1)"""
    await check_rate_limit(request, "global")
    if not _SYMBOL_RE.match(symbol.strip().upper().replace(".NS","")):
        raise HTTPException(status_code=422, detail="Invalid symbol")
    news = await news_fetcher.get_symbol_news(symbol, limit=limit)
    sentiment = await news_fetcher.get_symbol_sentiment(symbol)
    return {"symbol": symbol.upper(), "news": news, "sentiment": sentiment, "timestamp": datetime.utcnow().isoformat()}


@router.get("/fundamentals/{symbol}")
async def get_fundamentals(symbol: str, request: Request):
    """Fundamentals scoring (Engine #2)"""
    await check_rate_limit(request, "global")
    if not _SYMBOL_RE.match(symbol.strip().upper().replace(".NS","")):
        raise HTTPException(status_code=422, detail="Invalid symbol")
    result = await fundamentals_engine.get_fundamentals(symbol)
    if "error" in result and result.get("score") is None:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/math/position")
async def calc_position(request: Request, body: dict):
    """Math engine — position sizing & Kelly (Engine #3)"""
    await check_rate_limit(request, "global")
    try:
        cap = float(body.get("capital", 100000))
        entry = float(body.get("entry"))
        stop = float(body.get("stop"))
        risk_pct = float(body.get("risk_pct", 0.01))
        win_prob = body.get("win_prob")
        payoff = body.get("payoff_ratio")
        if win_prob is not None:
            win_prob = float(win_prob)
        if payoff is not None:
            payoff = float(payoff)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid numeric fields: need entry, stop, capital")
    sizing = math_engine.position_size(cap, entry, stop, risk_pct, win_prob, payoff)
    atr_lv = None
    if body.get("atr"):
        try:
            atr_lv = math_engine.atr_levels(entry, float(body["atr"]), body.get("direction", "BUY"))
        except Exception:
            pass
    return {"sizing": sizing, "atr_levels": atr_lv}


@router.post("/math/atr")
async def calc_atr(request: Request, body: dict):
    await check_rate_limit(request, "global")
    try:
        entry = float(body["entry"])
        atr = float(body["atr"])
        direction = body.get("direction", "BUY")
    except Exception:
        raise HTTPException(status_code=422, detail="Need entry, atr")
    return math_engine.atr_levels(entry, atr, direction)


@router.get("/strategy/rules")
async def list_strategy_rules(request: Request):
    """List active auto-generated rules (Engine #4)"""
    await check_rate_limit(request, "global")
    from ai_agent.strategy_generator import strategy_generator

    return await strategy_generator.evaluate_stored_rules()


@router.post("/strategy/generate")
async def generate_strategy(request: Request, body: dict = None, _auth=Depends(verify_api_key_optional)):
    """Generate new rules — dry_run true by default"""
    await check_rate_limit(request, "auth")
    from ai_agent.strategy_generator import strategy_generator

    lookback = int((body or {}).get("lookback_days", 14))
    dry_run = bool((body or {}).get("dry_run", True))
    # Only allow live generation with auth if API key is set
    if not dry_run:
        # Requires auth
        from api.deps import _get_expected_key

        if _get_expected_key() and _auth in (None, "open"):
            raise HTTPException(status_code=401, detail="Live rule generation requires X-API-Key")
    result = await strategy_generator.generate_rules(lookback_days=lookback, dry_run=dry_run)
    return result
