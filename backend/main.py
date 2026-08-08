"""
AI Trader — Main Application

Architecture:
  - FastAPI with lifespan-based startup/shutdown
  - ARTH AI Agent initialized at startup
  - Learning scheduler starts after ARTH is ready
  - CORS configured for development (frontend URL from settings)
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings, is_market_open
from api.routes import (
    prices, signals,
    arth as arth_routes,
    backtest as backtest_routes,
    analysis as analysis_routes,
    paper_trading as paper_routes,
    websocket as ws_routes,
)
from ai_agent.arth import arth
from ai_agent.scheduler import scheduler
from database.manager import get_db_path

# ─── Logging ────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─── Lifespan ───────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("=" * 60)
    logger.info(f"  {settings.app_name} v2.0 — Starting")
    logger.info(f"  Database: {get_db_path()}")
    logger.info("=" * 60)
    
    # Initialize ARTH
    await arth.initialize()
    
    # Start learning scheduler (non-blocking)
    await scheduler.start()
    
    logger.info("All systems operational. Ready for requests.")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await scheduler.stop()
    await arth.shutdown()
    logger.info("Shutdown complete.")


# ─── App ────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    description="Self-learning AI trading signals for Indian markets (NSE)",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — Architecture Fix: Use specific origins, not wildcard with credentials
allowed_origins = [
    settings.frontend_url,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ────────────────────────────────────────────────────

app.include_router(prices.router)
app.include_router(signals.router)
app.include_router(arth_routes.router)
app.include_router(backtest_routes.router)
app.include_router(analysis_routes.router)
app.include_router(paper_routes.router)
app.include_router(ws_routes.router)


# ─── Root & Health ──────────────────────────────────────────────

@app.get("/", tags=["Root"])
async def root():
    return {
        "name": settings.app_name,
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "arth": {
            "status": arth.status,
            "brain": arth.brain.get_stats() if arth.brain else {},
        },
        "endpoints": {
            "prices": "/api/prices",
            "signals": "/api/signals",
            "arth": "/api/arth/analyze/{symbol}",
            "backtest": "/api/backtest/run",
            "paper": "/api/paper/portfolio",
        },
    }


@app.get("/api/health", tags=["Health"])
async def health():
    """
    Health check with market status and brain stats.
    
    Architecture Fix: Uses timezone-aware IST check instead of
    broken UTC float-to-int comparison.
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "market_status": "open" if is_market_open() else "closed",
        "arth_status": arth.status,
        "ai_enabled": arth.status == "ready",
        "ai_providers": arth.get_provider_status() if arth.status == "ready" else [],
        "brain_stats": arth.brain.get_stats() if arth.brain else {},
        "database": str(get_db_path()),
    }
