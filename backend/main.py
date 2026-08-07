"""
AI Trader - Main Application
Phase 1: FastAPI Backend with Rule-Based Signals
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from api.routes import prices, signals

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info(f"Starting {settings.app_name} v1.0...")
    logger.info("Phase 1: Rule-based signals (No AI required)")
    yield
    logger.info("Shutting down AI Trader...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="""
## AI Trader - Phase 1: Foundation

A free trading signal platform for Indian markets (Nifty 50, Nifty Bank).

### Features
- 🟢 Real-time BUY/SELL/HOLD signals
- 📊 Technical indicators (SMA, RSI, MACD)
- 📈 Interactive charts
- ⚡ Yahoo Finance data (FREE)

### Future Phases
- 🤖 AI-powered analysis (ARTH)
- 🔄 Multi-AI provider integration
- 📚 Self-learning pattern recognition
- 📉 Backtesting engine

### Getting Started
1. Run backend: `uvicorn backend.main:app --reload`
2. Run frontend: `cd frontend && npm run dev`
3. Open: http://localhost:3000
    """,
    version="1.0.0",
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


@app.get("/", tags=["Root"])
async def root():
    """API info"""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "phase": "1 - Foundation",
        "status": "running",
        "docs": "/docs",
        "ai_enabled": False,
        "endpoints": {
            "prices": "/api/prices",
            "signals": "/api/signals",
            "indices": "/api/prices/indices/summary",
            "overview": "/api/signals/summary/overview"
        }
    }


@app.get("/api/health", tags=["Health"])
async def health():
    """Health check"""
    from backend.services.price_fetcher import price_fetcher
    indices = await price_fetcher.get_index_data()
    
    # Check if market is open (NSE: 9:15 AM - 3:30 PM IST)
    now = datetime.utcnow()
    market_open = 3.75 <= now.hour < 12.5  # Simplified check
    
    return {
        "status": "healthy",
        "service": settings.app_name,
        "timestamp": datetime.utcnow().isoformat(),
        "ai_enabled": False,
        "data_source": "Yahoo Finance (FREE)",
        "indices_loaded": len(indices) > 0
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug
    )
