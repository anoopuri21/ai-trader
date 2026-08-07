"""
AI Trader - Configuration Module
Full configuration for all phases
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
    
    # Trading Parameters
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
    
    # AI Provider Keys
    groq_api_key: Optional[str] = None
    cohere_api_key: Optional[str] = None
    huggingface_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # AI Settings
    ai_priority: str = "groq,cohere,huggingface,ollama"
    enable_fallback_signals: bool = True
    
    # Learning & Backtesting
    enable_backtesting: bool = True
    backtest_schedule: str = "daily"
    backtest_start_date: str = "2020-01-01"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
