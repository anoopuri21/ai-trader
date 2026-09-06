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
    omniroute as omniroute_routes,
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

_is_prod = getattr(settings, "env", "development") == "production"

app = FastAPI(
    title=settings.app_name,
    description="Self-learning AI trading signals for Indian markets (NSE) — OmniRoute gateway + 4 self-learning engines",
    version="2.1.0",
    lifespan=lifespan,
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
    openapi_url="/openapi.json" if not _is_prod else None,
)

# CORS — strict, validates frontend_url != "*"
if settings.frontend_url.strip() == "*":
    raise ValueError("FRONTEND_URL cannot be '*'. Set a specific origin when allow_credentials=True")

_allowed = [settings.frontend_url, "http://localhost:3000", "http://127.0.0.1:3000"]
_allowed = [o.strip().rstrip("/") for o in _allowed if o.strip()]
allowed_origins = list(dict.fromkeys(_allowed))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Request-Id"],
    max_age=600,
)

# Rate limit middleware (global 60/min)
from middleware.rate_limit import RateLimitMiddleware

app.add_middleware(RateLimitMiddleware, exclude_paths=["/docs", "/openapi.json", "/redoc", "/api/health"])

# ─── Routers ────────────────────────────────────────────────────

app.include_router(prices.router)
app.include_router(signals.router)
app.include_router(arth_routes.router)
app.include_router(backtest_routes.router)
app.include_router(analysis_routes.router)
app.include_router(paper_routes.router)
app.include_router(ws_routes.router)
app.include_router(omniroute_routes.router)


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
    In production (debug=False) hides database path and detailed brain.
    """
    is_debug = getattr(settings, "debug", False)
    base = {
        "status": "healthy",
        "service": settings.app_name,
        "version": "2.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "market_status": "open" if is_market_open() else "closed",
        "arth_status": arth.status,
        "ai_enabled": arth.status == "ready",
    }
    if is_debug:
        base["ai_providers"] = arth.get_provider_status() if arth.status == "ready" else []
        base["brain_stats"] = arth.brain.get_stats() if arth.brain else {}
        base["database"] = str(get_db_path())
    else:
        base["ai_providers"] = [{"provider": p["provider"], "available": p["available"]} for p in (arth.get_provider_status() if arth.status == "ready" else [])]
        base["brain_stats"] = {"total_predictions": (arth.brain.get_stats().get("total_predictions", 0) if arth.brain else 0)}
    return base
