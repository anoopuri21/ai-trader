"""
ARTH's Sentiment Analyzer
Uses free news sources for market sentiment
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Analyze market sentiment from free sources"""
    
    def __init__(self):
        self._cache: Dict = {}
        self._cache_time: Optional[datetime] = None
    
    async def get_market_sentiment(self) -> Dict:
        """Get overall market sentiment"""
        sentiment = {
            "overall": "NEUTRAL",
            "confidence": 50,
            "fear_greed": 50,
            "factors": [],
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Calculate from market data (free, no API needed)
        try:
            market_data = await self._get_market_data()
            if market_data:
                sentiment.update(self._calculate_sentiment_from_data(market_data))
        except Exception as e:
            logger.error(f"Error calculating sentiment: {e}")
        
        return sentiment
    
    async def _get_market_data(self) -> Optional[Dict]:
        """Get market data for sentiment calculation"""
        try:
            import yfinance as yf
            
            # Get VIX equivalent for India (India VIX)
            vix = yf.Ticker("^INDIAVIX")
            vix_info = vix.fast_info
            
            # Get Nifty for trend
            nifty = yf.Ticker("^NSEI")
            nifty_info = nifty.fast_info
            nifty_hist = nifty.history(period="5d")
            
            data = {
                "vix": float(vix_info.last_price) if vix_info.last_price else None,
                "nifty": float(nifty_info.last_price) if nifty_info.last_price else None,
                "nifty_change": 0,
            }
            
            # Calculate recent Nifty trend
            if nifty_hist is not None and len(nifty_hist) >= 2:
                start = nifty_hist['Close'].iloc[0]
                end = nifty_hist['Close'].iloc[-1]
                data['nifty_change'] = ((end - start) / start) * 100
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            return None
    
    def _calculate_sentiment_from_data(self, data: Dict) -> Dict:
        """Calculate sentiment from market data"""
        factors = []
        score = 50  # Neutral baseline
        
        # VIX analysis (lower VIX = less fear)
        if data.get('vix'):
            vix = data['vix']
            if vix < 12:
                score += 15
                factors.append("Very low volatility - complacent market")
            elif vix < 15:
                score += 10
                factors.append("Low volatility - calm market")
            elif vix < 20:
                score += 0
                factors.append("Normal volatility")
            elif vix < 25:
                score -= 10
                factors.append("Elevated volatility - cautious")
            else:
                score -= 20
                factors.append("High volatility - fear in market")
        
        # Nifty trend
        nifty_change = data.get('nifty_change', 0)
        if nifty_change > 2:
            score += 15
            factors.append(f"Strong bullish trend ({nifty_change:.1f}% in 5 days)")
        elif nifty_change > 0.5:
            score += 5
            factors.append(f"Mild bullish trend ({nifty_change:.1f}%)")
        elif nifty_change < -2:
            score -= 15
            factors.append(f"Strong bearish trend ({nifty_change:.1f}% in 5 days)")
        elif nifty_change < -0.5:
            score -= 5
            factors.append(f"Mild bearish trend ({nifty_change:.1f}%)")
        
        # Clamp score
        score = max(0, min(100, score))
        
        # Determine overall sentiment
        if score >= 65:
            overall = "BULLISH"
        elif score >= 45:
            overall = "NEUTRAL"
        else:
            overall = "BEARISH"
        
        return {
            "overall": overall,
            "confidence": abs(score - 50) * 2,  # Higher deviation = more confident
            "fear_greed": score,
            "factors": factors,
        }
    
    async def get_stock_sentiment(self, symbol: str) -> Dict:
        """Get sentiment for a specific stock"""
        try:
            import yfinance as yf
            ticker = yf.Ticker(f"{symbol}.NS")
            
            # Get recent performance
            hist = ticker.history(period="1mo")
            if hist is None or hist.empty:
                return {"sentiment": "NEUTRAL", "confidence": 0, "factors": []}
            
            # Calculate metrics
            returns = hist['Close'].pct_change().dropna()
            volatility = returns.std() * (252 ** 0.5) * 100  # Annualized
            recent_return = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
            
            # Volume trend
            vol_recent = hist['Volume'].tail(5).mean()
            vol_avg = hist['Volume'].mean()
            vol_ratio = vol_recent / vol_avg if vol_avg > 0 else 1
            
            factors = []
            score = 50
            
            if recent_return > 5:
                score += 15
                factors.append(f"Strong recent performance (+{recent_return:.1f}%)")
            elif recent_return > 0:
                score += 5
                factors.append(f"Positive recent return (+{recent_return:.1f}%)")
            elif recent_return < -5:
                score -= 15
                factors.append(f"Weak recent performance ({recent_return:.1f}%)")
            elif recent_return < 0:
                score -= 5
                factors.append(f"Negative recent return ({recent_return:.1f}%)")
            
            if vol_ratio > 1.5:
                if recent_return > 0:
                    score += 10
                    factors.append("High volume buying interest")
                else:
                    score -= 10
                    factors.append("High volume selling pressure")
            
            score = max(0, min(100, score))
            
            return {
                "sentiment": "BULLISH" if score >= 60 else "BEARISH" if score <= 40 else "NEUTRAL",
                "confidence": min(90, abs(score - 50) * 2),
                "fear_greed": score,
                "factors": factors,
                "metrics": {
                    "monthly_return": round(recent_return, 2),
                    "volatility": round(volatility, 2),
                    "volume_ratio": round(vol_ratio, 2),
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting stock sentiment for {symbol}: {e}")
            return {"sentiment": "NEUTRAL", "confidence": 0, "factors": []}


# Singleton
sentiment_analyzer = SentimentAnalyzer()
