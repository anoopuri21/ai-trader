"""
AI Trader — Configuration Module

Architecture: Single source of truth for all settings.
Uses IST timezone for market hours (NSE operates in IST).
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env from the project root (parent of backend/)
_project_root = Path(__file__).parent.parent
_env_path = _project_root / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

# Indian Standard Time — NSE operates in IST
IST = ZoneInfo("Asia/Kolkata")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # ─── Application ───
    app_name: str = "AI Trader"
    debug: bool = True
    port: int = 8000
    frontend_url: str = "http://localhost:3000"
    
    # ─── Database ───
    # Note: The actual DB path is managed by database/manager.py.
    # This field is kept for backward compatibility but not used directly.
    database_url: str = "sqlite:///./data/ai_trader.db"
    
    # ─── Trading Parameters ───
    rsi_period: int = 14
    sma_short: int = 20
    sma_mid: int = 50
    sma_long: int = 200
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    
    # ─── Signal Settings ───
    min_signal_confidence: int = 60
    rsi_oversold: int = 30
    rsi_overbought: int = 70
    
    # ─── Risk Management (ATR-based) ───
    atr_period: int = 14
    atr_stop_multiplier: float = 1.5    # Stop-loss = Entry - 1.5 * ATR
    atr_target_multiplier: float = 3.0  # Target = Entry + 3.0 * ATR
    max_stop_pct: float = 0.05          # Hard cap: 5% max stop
    min_stop_pct: float = 0.01          # Hard cap: 1% min stop
    max_target_pct: float = 0.10        # Hard cap: 10% max target
    min_rr_ratio: float = 1.5           # Minimum risk:reward ratio
    
    # ─── Rate Limits ───
    price_update_interval: int = 30
    sse_timeout: int = 300
    
    # ─── Logging ───
    log_level: str = "INFO"
    
    # ─── AI Provider Keys ───
    groq_api_key: Optional[str] = None
    cohere_api_key: Optional[str] = None
    huggingface_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # ─── AI Settings ───
    ai_priority: str = "groq,cohere,huggingface,ollama"
    enable_fallback_signals: bool = True
    
    # ─── Learning & Backtesting ───
    enable_backtesting: bool = True
    backtest_schedule: str = "daily"
    backtest_start_date: str = "2020-01-01"
    
    # ─── Transaction Costs (for realistic backtesting) ───
    slippage_pct: float = 0.001    # 0.1% slippage per trade
    stt_pct: float = 0.0004        # Securities Transaction Tax ~0.04%
    brokerage_pct: float = 0.0003  # Brokerage ~0.03%
    
    model_config = {"env_file": str(_env_path), "case_sensitive": False}


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def is_market_open() -> bool:
    """
    Check if NSE is currently open.
    NSE hours: 9:15 AM – 3:30 PM IST, Monday–Friday.
    
    Architecture Fix: Previously used datetime.utcnow() with a broken
    float-to-int comparison (3.75 <= now.hour). This was mathematically
    impossible since hour is always an integer. Now uses IST timezone
    and checks both hours AND minutes.
    """
    now = datetime.now(IST)
    
    # Weekend check
    if now.weekday() >= 5:
        return False
    
    # Time check: 9:15 AM to 3:30 PM IST
    market_open = now.hour * 60 + now.minute  # minutes since midnight
    return 555 <= market_open < 930  # 9:15 = 555, 15:30 = 930


# Need datetime for is_market_open
from datetime import datetime
