"""
AI Trader - ARTH AI Agent API Routes
"""

import re as _re
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request, Depends
from pydantic import BaseModel, Field
from datetime import datetime

from ai_agent.arth import arth
from api.deps import verify_api_key_optional
from middleware.rate_limit import check_rate_limit

_SYMBOL_RE = _re.compile(r"^[A-Z0-9]{1,12}$")

router = APIRouter(prefix="/api/arth", tags=["ARTH AI Agent"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="Chat message")
    context: Optional[dict] = None

    @classmethod
    def _sanitize(cls, v):
        # limit nesting depth handled by pydantic
        return v


@router.get("/analyze/{symbol}")
async def analyze_stock(symbol: str, request: Request):
    """
    Get ARTH's complete AI analysis for a stock.
    Combines rule-based signals with AI analysis.
    """
    await check_rate_limit(request, "strict")
    sym = symbol.strip().upper().replace(".NS", "")
    if not _SYMBOL_RE.match(sym):
        raise HTTPException(status_code=422, detail="Invalid symbol")
    result = await arth.analyze_stock(sym)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/chat")
async def chat_with_arth(req: Request, body: ChatRequest, _auth=Depends(verify_api_key_optional)):
    """
    Chat with ARTH about markets, stocks, and trading.
    Ask about analysis, performance, strategies, etc.
    """
    await check_rate_limit(req, "strict")
    # Sanitize message length already via Field; also strip control chars
    msg = body.message.strip()
    if len(msg) > 2000:
        raise HTTPException(status_code=422, detail="Message too long")
    result = await arth.chat(msg, body.context)
    return result


@router.get("/brain/stats")
async def brain_stats(request: Request, _auth=Depends(verify_api_key_optional)):
    """Get ARTH's brain statistics — hides details when debug=False and no auth"""
    if not arth.brain:
        raise HTTPException(status_code=503, detail="ARTH brain not initialized")
    # Privacy: if not debug and no API key, return summary only
    from config import settings as _s

    is_debug = getattr(_s, "debug", False)
    auth_ok = _auth is not None and _auth != "open"
    if not is_debug and not auth_ok:
        stats = arth.brain.get_stats()
        return {
            "stats": {"total_predictions": stats.get("total_predictions", 0), "overall_accuracy": stats.get("overall_accuracy", 0)},
            "accuracy_30d": {"accuracy": arth.brain.get_prediction_accuracy(7).get("accuracy", 0)},
            "top_patterns": [],
            "active_rules": stats.get("active_rules", 0),
            "rules_sample": [],
            "timestamp": datetime.utcnow().isoformat(),
            "note": "Detailed stats require debug=True or X-API-Key",
        }
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
async def self_reflect(request: Request, days: int = Query(7, ge=1, le=90), _auth=Depends(verify_api_key_optional)):
    """Trigger ARTH self-reflection and learning — rate limited"""
    await check_rate_limit(request, "auth")
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
async def get_probability(symbol: str, request: Request):
    """Get trade probability for a symbol"""
    await check_rate_limit(request, "strict")
    sym = symbol.strip().upper().replace(".NS", "")
    if not _SYMBOL_RE.match(sym):
        raise HTTPException(status_code=422, detail="Invalid symbol")
    result = await arth.get_probability(sym)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
