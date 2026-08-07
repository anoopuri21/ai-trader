"""
AI Trader - ARTH AI Agent API Routes
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime

from ai_agent.arth import arth

router = APIRouter(prefix="/api/arth", tags=["ARTH AI Agent"])


class ChatRequest(BaseModel):
    message: str
    context: Optional[dict] = None


@router.get("/analyze/{symbol}")
async def analyze_stock(symbol: str):
    """
    Get ARTH's complete AI analysis for a stock.
    Combines rule-based signals with AI analysis.
    """
    result = await arth.analyze_stock(symbol.upper())
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/chat")
async def chat_with_arth(request: ChatRequest):
    """
    Chat with ARTH about markets, stocks, and trading.
    Ask about analysis, performance, strategies, etc.
    """
    result = await arth.chat(request.message, request.context)
    return result


@router.get("/brain/stats")
async def brain_stats():
    """Get ARTH's brain statistics"""
    if not arth.brain:
        raise HTTPException(status_code=503, detail="ARTH brain not initialized")
    
    stats = arth.brain.get_stats()
    accuracy = arth.brain.get_prediction_accuracy(30)
    patterns = arth.brain.get_top_patterns()
    rules = arth.brain.get_active_rules()
    
    return {
        "stats": stats,
        "accuracy_30d": accuracy,
        "top_patterns": patterns[:10],
        "active_rules": len(rules),
        "rules_sample": rules[:10],
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/brain/predictions")
async def get_predictions(limit: int = Query(50, ge=1, le=200)):
    """Get recent predictions"""
    if not arth.brain:
        raise HTTPException(status_code=503, detail="ARTH brain not initialized")
    
    predictions = arth.brain.get_recent_predictions(limit)
    return {
        "count": len(predictions),
        "predictions": predictions,
    }


@router.get("/brain/patterns")
async def get_patterns():
    """Get all learned patterns"""
    if not arth.brain:
        raise HTTPException(status_code=503, detail="ARTH brain not initialized")
    
    patterns = arth.brain.get_top_patterns(min_uses=1)
    return {
        "count": len(patterns),
        "patterns": patterns,
    }


@router.get("/brain/rules")
async def get_rules():
    """Get all active learning rules"""
    if not arth.brain:
        raise HTTPException(status_code=503, detail="ARTH brain not initialized")
    
    rules = arth.brain.get_active_rules()
    return {
        "count": len(rules),
        "rules": rules,
    }


@router.post("/reflect")
async def self_reflect(days: int = Query(7, ge=1, le=90)):
    """Trigger ARTH self-reflection and learning"""
    result = await arth.self_reflect(days)
    return result


@router.get("/status")
async def arth_status():
    """Get ARTH's current status"""
    return {
        "status": arth.status,
        "providers": arth.get_provider_status(),
        "initialized": arth._initialized,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/probability/{symbol}")
async def get_probability(symbol: str):
    """Get trade probability for a symbol"""
    result = await arth.get_probability(symbol.upper())
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
