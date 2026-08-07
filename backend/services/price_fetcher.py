"""
AI Trader - Price Fetcher Service
Phase 1: Yahoo Finance integration (FREE)
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
    """
    Fetches real-time stock data from Yahoo Finance.
    Yahoo Finance is FREE and provides ~15 min delayed data for NSE stocks.
    """
    
    def __init__(self):
        # Cache for 30 seconds to avoid rate limiting
        self._price_cache = TTLCache(maxsize=100, ttl=30)
        self._data_cache = TTLCache(maxsize=50, ttl=60)
    
    def _get_symbol(self, symbol: str) -> str:
        """Convert symbol to Yahoo Finance format"""
        if symbol.startswith("^"):
            return symbol  # Index symbol
        if not symbol.endswith(".NS"):
            return f"{symbol}.NS"
        return symbol
    
    def _get_display_symbol(self, yahoo_symbol: str) -> str:
        """Convert Yahoo Finance symbol back to display format"""
        return yahoo_symbol.replace(".NS", "").replace(".BO", "")
    
    def _get_company_name(self, symbol: str) -> str:
        """Get company name for symbol"""
        names = {
            "RELIANCE": "Reliance Industries",
            "TCS": "Tata Consultancy Services",
            "HDFCBANK": "HDFC Bank",
            "ICICIBANK": "ICICI Bank",
            "SBIN": "State Bank of India",
            "BHARTIARTL": "Bharti Airtel",
            "ITC": "ITC Limited",
            "KOTAKBANK": "Kotak Mahindra Bank",
            "LT": "Larsen & Toubro",
            "HINDUNILVR": "Hindustan Unilever",
            "SUNPHARMA": "Sun Pharmaceutical",
            "MARUTI": "Maruti Suzuki India",
            "TATAMOTORS": "Tata Motors",
            "TATASTEEL": "Tata Steel",
            "AXISBANK": "Axis Bank",
            "BAJFINANCE": "Bajaj Finance",
            "NTPC": "NTPC Limited",
            "POWERGRID": "Power Grid Corp",
            "ONGC": "Oil & Natural Gas Corp",
            "COALINDIA": "Coal India",
            "NESTLEIND": "Nestle India",
            "ULTRACEMCO": "UltraTech Cement",
            "ASIANPAINT": "Asian Paints",
            "HCLTECH": "HCL Technologies",
            "WIPRO": "Wipro Limited",
            "ADANIPORTS": "Adani Ports",
            "INDUSINDBK": "IndusInd Bank",
            "BANDHANBNK": "Bandhan Bank",
            "IDFCFIRSTB": "IDFC First Bank",
            "AUBANK": "AU Small Finance Bank",
            "FEDERALBNK": "Federal Bank",
            "PNB": "Punjab National Bank",
            "CANBK": "Canara Bank",
            "BANKOFBARODA": "Bank of Baroda",
            "SBICARD": "SBI Cards",
            "TATAINVEST": "Tata Investment Corp",
            "M&MFIN": "M&M Financial",
            "TITAN": "Titan Company",
            "BAJAJFINSV": "Bajaj Finserv",
            "SHRIRAMFIN": "Shriram Finance",
            "INFY": "Infosys",
        }
        return names.get(symbol, symbol)
    
    async def get_price(self, symbol: str) -> Optional[StockInfo]:
        """Get current price for a single stock"""
        cache_key = f"price_{symbol}"
        if cache_key in self._price_cache:
            return self._price_cache[cache_key]
        
        try:
            ticker = yf.Ticker(self._get_symbol(symbol))
            info = ticker.fast_info
            
            if info.last_price is None or info.last_price == 0:
                return None
            
            stock = StockInfo(
                symbol=symbol.upper(),
                name=self._get_company_name(symbol),
                current_price=float(info.last_price),
                previous_close=float(info.previous_close or info.last_price),
                change=float(info.last_price - (info.previous_close or info.last_price)),
                change_percent=float(
                    ((info.last_price - (info.previous_close or info.last_price)) / 
                     (info.previous_close or info.last_price) * 100) 
                    if info.previous_close else 0
                ),
                open=float(info.open or info.last_price),
                high=float(info.day_high or info.last_price),
                low=float(info.day_low or info.last_price),
                volume=int(info.last_volume or 0),
                timestamp=datetime.utcnow()
            )
            
            self._price_cache[cache_key] = stock
            return stock
            
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None
    
    async def get_prices(self, symbols: List[str]) -> List[StockInfo]:
        """Get prices for multiple stocks concurrently"""
        tasks = [self.get_price(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, StockInfo)]
    
    async def get_historical_data(
        self, 
        symbol: str, 
        period: str = "3mo",
        interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """Get historical data for technical analysis"""
        cache_key = f"hist_{symbol}_{period}_{interval}"
        if cache_key in self._data_cache:
            return self._data_cache[cache_key]
        
        try:
            ticker = yf.Ticker(self._get_symbol(symbol))
            df = ticker.history(period=period, interval=interval)
            
            if df is not None and not df.empty:
                self._data_cache[cache_key] = df
                return df
            
            return None
        except Exception as e:
            logger.error(f"Error fetching history for {symbol}: {e}")
            return None
    
    async def get_index_data(self) -> Dict[str, Dict]:
        """Get Nifty 50 and Nifty Bank index data"""
        result = {}
        
        try:
            # Nifty 50
            nifty = yf.Ticker("^NSEI")
            nifty_info = nifty.fast_info
            
            if nifty_info.last_price:
                result["^NSEI"] = {
                    "index_name": "Nifty 50",
                    "current_value": float(nifty_info.last_price),
                    "change": float(nifty_info.last_price - (nifty_info.previous_close or nifty_info.last_price)),
                    "change_percent": float(
                        ((nifty_info.last_price - (nifty_info.previous_close or nifty_info.last_price)) / 
                         (nifty_info.previous_close or nifty_info.last_price) * 100)
                        if nifty_info.previous_close else 0
                    ),
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Nifty Bank
            bank = yf.Ticker("^NSEBANK")
            bank_info = bank.fast_info
            
            if bank_info.last_price:
                result["^NSEBANK"] = {
                    "index_name": "Nifty Bank",
                    "current_value": float(bank_info.last_price),
                    "change": float(bank_info.last_price - (bank_info.previous_close or bank_info.last_price)),
                    "change_percent": float(
                        ((bank_info.last_price - (bank_info.previous_close or bank_info.last_price)) / 
                         (bank_info.previous_close or bank_info.last_price) * 100)
                        if bank_info.previous_close else 0
                    ),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error fetching index data: {e}")
        
        return result


# Singleton instance
price_fetcher = PriceFetcher()
