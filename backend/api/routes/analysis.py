"""
AI Trader - Advanced Analysis API Routes
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime

from services.price_fetcher import price_fetcher
from services.advanced_indicators import advanced_indicators
from ai_agent.sentiment import sentiment_analyzer

router = APIRouter(prefix="/api/analysis", tags=["Advanced Analysis"])


@router.get("/advanced/{symbol}")
async def get_advanced_analysis(symbol: str):
    """Get all advanced technical indicators for a stock"""
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
async def get_fibonacci(symbol: str):
    """Get Fibonacci retracement levels"""
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
async def get_pivot_points(symbol: str):
    """Get pivot points for a stock"""
    stock = await price_fetcher.get_price(symbol.upper())
    if not stock:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")
    
    pivots = advanced_indicators.calculate_pivot_points(stock.high, stock.low, stock.current_price)
    return {
        "symbol": symbol.upper(),
        "pivot_points": pivots,
        "current_price": stock.current_price,
    }
