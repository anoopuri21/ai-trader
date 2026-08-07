"""
AI Trader - Configuration Module
Phase 1: Foundation with rule-based signals
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_name: str = "AI Trader"
    debug: bool = True
    port: int = 8000
    frontend_url: str = "http://localhost:3000"
    
    # Database
    database_url: str = "sqlite:///./ai_trader.db"
    
    # Trading Parameters (Rule-based)
    rsi_period: int = 14
    sma_short: int = 20
    sma_mid: int = 50
    sma_long: int = 200
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    
    # Signal Settings
    min_signal_confidence: int = 60
    rsi_oversold: int = 30
    rsi_overbought: int = 70
    
    # Rate Limits
    price_update_interval: int = 30
    sse_timeout: int = 300
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
