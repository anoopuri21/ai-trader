"""
AI Trader - Main Application
Full Stack: FastAPI + ARTH AI Agent + Learning Engine + Backtesting
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from api.routes import prices, signals, arth as arth_routes, backtest as backtest_routes, analysis as analysis_routes, paper_trading as paper_routes, websocket as ws_routes
from ai_agent.arth import arth
from ai_agent.scheduler import scheduler

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info(f"Starting {settings.app_name} v2.0...")
    logger.info("Initializing ARTH AI Agent...")
    await arth.initialize()
    logger.info("ARTH is ready!")
    await scheduler.start()
    yield
    logger.info("Shutting down AI Trader...")
    await scheduler.stop()
    await arth.shutdown()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="""
## AI Trader v2.0 — ARTH AI Trading Agent

A self-learning trading signal platform for Indian markets (Nifty 50, Nifty Bank).

### Features
- 🤖 ARTH - AI Trading Agent with central brain
- 🟢 Real-time BUY/SELL/HOLD signals
- 📊 Technical indicators (SMA, RSI, MACD, Bollinger, ATR)
- 📈 Interactive charts with pattern recognition
- ⚡ Multi-AI provider (Groq, Cohere, HuggingFace, Ollama)
- 🧠 Self-learning from every prediction
- 📉 Backtesting engine with historical validation
- 🎯 Risk-reward calculation with probability scores
    """,
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(prices.router)
app.include_router(signals.router)
app.include_router(arth_routes.router)
app.include_router(backtest_routes.router)
app.include_router(analysis_routes.router)
app.include_router(paper_routes.router)
app.include_router(ws_routes.router)


@app.get("/", tags=["Root"])
async def root():
    """API info"""
    return {
        "name": settings.app_name,
        "version": "2.0.0",
        "phase": "Full Stack - ARTH AI Agent",
        "status": "running",
        "docs": "/docs",
        "arth": {
            "status": arth.status,
            "brain_size": arth.brain.get_stats() if arth.brain else {},
        },
        "endpoints": {
            "prices": "/api/prices",
            "signals": "/api/signals",
            "arth_analyze": "/api/arth/analyze/{symbol}",
            "arth_chat": "/api/arth/chat",
            "arth_brain": "/api/arth/brain/stats",
            "backtest": "/api/backtest/run",
            "probability": "/api/probability/{symbol}",
        }
    }


@app.get("/api/health", tags=["Health"])
async def health():
    """Health check"""
    from services.price_fetcher import price_fetcher
    indices = await price_fetcher.get_index_data()

    now = datetime.utcnow()
    market_open = 3.75 <= now.hour < 12.5

    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "arth_status": arth.status,
        "ai_enabled": arth.status == "ready",
        "ai_providers": arth.get_provider_status() if arth.status == "ready" else [],
        "data_source": "Yahoo Finance (FREE)",
        "market_status": "open" if market_open else "closed",
        "indices_loaded": len(indices) > 0,
        "brain_stats": arth.brain.get_stats() if arth.brain else {},
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug
    )
