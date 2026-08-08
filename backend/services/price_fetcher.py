"""
AI Trader — Price Fetcher Service
Yahoo Finance integration (FREE).

Architecture: Added batch download support for fetching multiple
stocks efficiently. Cache uses TTL to prevent Yahoo rate limiting.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
import asyncio

import yfinance as yf
import pandas as pd
from cachetools import TTLCache

from config import settings
from models.stock import StockInfo, NIFTY_50_SYMBOLS, NIFTY_BANK_SYMBOLS

logger = logging.getLogger(__name__)


class PriceFetcher:
    """Fetches real-time stock data from Yahoo Finance."""
    
    def __init__(self):
        self._price_cache = TTLCache(maxsize=100, ttl=30)
        self._data_cache = TTLCache(maxsize=50, ttl=60)
        self._company_names = {
            "RELIANCE": "Reliance Industries", "TCS": "Tata Consultancy Services",
            "HDFCBANK": "HDFC Bank", "ICICIBANK": "ICICI Bank", "SBIN": "State Bank of India",
            "BHARTIARTL": "Bharti Airtel", "ITC": "ITC Limited",
            "KOTAKBANK": "Kotak Mahindra Bank", "LT": "Larsen & Toubro",
            "HINDUNILVR": "Hindustan Unilever", "SUNPHARMA": "Sun Pharmaceutical",
            "MARUTI": "Maruti Suzuki India", "TATAMOTORS": "Tata Motors",
            "TATASTEEL": "Tata Steel", "AXISBANK": "Axis Bank",
            "BAJFINANCE": "Bajaj Finance", "NTPC": "NTPC Limited",
            "POWERGRID": "Power Grid Corp", "ONGC": "Oil & Natural Gas Corp",
            "COALINDIA": "Coal India", "NESTLEIND": "Nestle India",
            "ULTRACEMCO": "UltraTech Cement", "ASIANPAINT": "Asian Paints",
            "HCLTECH": "HCL Technologies", "WIPRO": "Wipro Limited",
            "ADANIPORTS": "Adani Ports", "INDUSINDBK": "IndusInd Bank",
            "BANDHANBNK": "Bandhan Bank", "IDFCFIRSTB": "IDFC First Bank",
            "AUBANK": "AU Small Finance Bank", "FEDERALBNK": "Federal Bank",
            "PNB": "Punjab National Bank", "CANBK": "Canara Bank",
            "BANKOFBARODA": "Bank of Baroda", "SBICARD": "SBI Cards",
            "TATAINVEST": "Tata Investment Corp", "M&MFIN": "M&M Financial",
            "TITAN": "Titan Company", "BAJAJFINSV": "Bajaj Finserv",
            "SHRIRAMFIN": "Shriram Finance", "INFY": "Infosys",
        }
    
    def _to_yahoo(self, symbol: str) -> str:
        """Convert symbol to Yahoo Finance format."""
        if symbol.startswith("^"):
            return symbol
        return symbol if symbol.endswith(".NS") else f"{symbol}.NS"
    
    def _from_yahoo(self, symbol: str) -> str:
        return symbol.replace(".NS", "").replace(".BO", "")
    
    async def get_price(self, symbol: str) -> Optional[StockInfo]:
        """Get current price for a single stock."""
        cache_key = f"price_{symbol}"
        if cache_key in self._price_cache:
            return self._price_cache[cache_key]
        
        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: yf.Ticker(self._to_yahoo(symbol)).fast_info)
            
            if not info.last_price or info.last_price == 0:
                return None
            
            prev = float(info.previous_close or info.last_price)
            last = float(info.last_price)
            
            stock = StockInfo(
                symbol=symbol.upper(),
                name=self._company_names.get(symbol, symbol),
                current_price=last,
                previous_close=prev,
                change=round(last - prev, 2),
                change_percent=round((last - prev) / prev * 100, 2) if prev else 0,
                open=float(info.open or last),
                high=float(info.day_high or last),
                low=float(info.day_low or last),
                volume=int(info.last_volume or 0),
                timestamp=datetime.utcnow(),
            )
            self._price_cache[cache_key] = stock
            return stock
        except Exception as e:
            logger.error(f"Price error {symbol}: {e}")
            return None
    
    async def get_prices(self, symbols: List[str]) -> List[StockInfo]:
        """Get prices for multiple stocks."""
        tasks = [self.get_price(s) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, StockInfo)]
    
    async def get_historical_data(self, symbol: str, period: str = "3mo", interval: str = "1d") -> Optional[pd.DataFrame]:
        """Get historical data for technical analysis."""
        cache_key = f"hist_{symbol}_{period}_{interval}"
        if cache_key in self._data_cache:
            return self._data_cache[cache_key]
        
        try:
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None, lambda: yf.Ticker(self._to_yahoo(symbol)).history(period=period, interval=interval)
            )
            if df is not None and not df.empty:
                self._data_cache[cache_key] = df
                return df
            return None
        except Exception as e:
            logger.error(f"Historical data error {symbol}: {e}")
            return None
    
    async def get_index_data(self) -> Dict[str, Dict]:
        """Get Nifty 50 and Bank Nifty index data."""
        result = {}
        for yahoo_sym, name in [("^NSEI", "Nifty 50"), ("^NSEBANK", "Nifty Bank")]:
            try:
                loop = asyncio.get_event_loop()
                info = await loop.run_in_executor(None, lambda s=yahoo_sym: yf.Ticker(s).fast_info)
                if info.last_price:
                    prev = float(info.previous_close or info.last_price)
                    last = float(info.last_price)
                    result[yahoo_sym] = {
                        "index_name": name,
                        "current_value": last,
                        "change": round(last - prev, 2),
                        "change_percent": round((last - prev) / prev * 100, 2) if prev else 0,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
            except Exception as e:
                logger.error(f"Index error {yahoo_sym}: {e}")
        return result


price_fetcher = PriceFetcher()
