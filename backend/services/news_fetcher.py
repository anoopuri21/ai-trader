"""
ARTH — Market News & Sentiment Engine (Engine #1)

Fetches market news from free sources (Yahoo Finance + optional NewsAPI)
and derives BULLISH / BEARISH / NEUTRAL sentiment via OmniRoute gateway.

Security:
  - Symbol allowlist:  NIFTY_50 + NIFTY_BANK + index tickers, or strict regex
  - No SSRF: only allow-listed domains (finance.yahoo.com, newsapi.org)
  - Timeouts + retries capped, no infinite loops
  - Prompt injection hardened: news text truncated + sanitized before AI
  - No eval / exec / pickle
"""

import asyncio
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any

import httpx
from cachetools import TTLCache

logger = logging.getLogger(__name__)

# ─── Config ─────────────────────────────────────────────────────────

# Only these domains are ever fetched (SSRF guard)
ALLOWED_NEWS_DOMAINS = ("finance.yahoo.com", "query1.finance.yahoo.com", "query2.finance.yahoo.com")

# Symbol validation — prevents path traversal / injection
_SYMBOL_RE = re.compile(r"^[A-Z0-9\.\^]{1,20}$")
from models.stock import NIFTY_50_SYMBOLS, NIFTY_BANK_SYMBOLS

ALLOWED_SYMBOLS = set(NIFTY_50_SYMBOLS + NIFTY_BANK_SYMBOLS + ["^NSEI", "^NSEBANK", "NIFTY", "BANKNIFTY", "INDIAVIX"])

# Cache: news per symbol 5 min, market sentiment 2 min
_news_cache = TTLCache(maxsize=200, ttl=300)
_sentiment_cache = TTLCache(maxsize=100, ttl=120)

# Fallback keywords for rule-based sentiment when AI unavailable
_BULLISH_KW = {"surge", "rally", "gain", "up", "bullish", "upgrade", "beat", "growth", "record", "high", "buy"}
_BEARISH_KW = {"fall", "drop", "down", "bearish", "downgrade", "miss", "loss", "cut", "low", "sell", "crash", "slump"}


def _validate_symbol(symbol: str) -> str:
    s = symbol.strip().upper()
    if not _SYMBOL_RE.match(s):
        raise ValueError(f"Invalid symbol: {symbol}")
    # Optionally restrict to allowlist for news (relaxed for analytics endpoints)
    return s


def _sanitize_text(text: str, max_len: int = 4000) -> str:
    """Strip control chars, truncate, prevent prompt injection via delimiters."""
    if not text:
        return ""
    # Remove null bytes / control chars except newline
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    # Neutralize common prompt injection markers
    text = text.replace("{{", "{ {").replace("}}", "} }").replace("```", "'''")
    return text[:max_len]


class NewsFetcher:
    """Fetch + score market news. Free tier: Yahoo Finance RSS/API, optional NewsAPI.org."""

    def __init__(self, newsapi_key: Optional[str] = None):
        self.newsapi_key = newsapi_key
        try:
            from config import settings

            self.newsapi_key = newsapi_key or getattr(settings, "newsapi_key", None)
        except Exception:
            pass

    # ─── Fetch ────────────────────────────────────────────────────

    async def get_symbol_news(self, symbol: str, limit: int = 8) -> List[Dict[str, Any]]:
        """Fetch recent headlines for a symbol via Yahoo Finance."""
        sym = _validate_symbol(symbol)
        cache_key = f"news:{sym}:{limit}"
        if cache_key in _news_cache:
            return _news_cache[cache_key]

        limit = max(1, min(limit, 20))  # clamp

        # Yahoo Finance search API (public, no key) — SSRF safe because domain is hard-coded
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={sym}.NS"
        headers = {"User-Agent": "AI-Trader/2.0 (news-fetcher)"}
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    logger.debug(f"Yahoo search {sym} -> {resp.status_code}")
                    return []
                data = resp.json()
                raw = data.get("news", [])[:limit]
                news = [
                    {
                        "title": _sanitize_text(n.get("title", ""), 200),
                        "publisher": _sanitize_text(n.get("publisher", ""), 80),
                        "link": n.get("link", "")[:500],
                        "type": n.get("type", "STORY"),
                        "published_at": n.get("providerPublishTime"),
                    }
                    for n in raw
                    if n.get("title")
                ]
                _news_cache[cache_key] = news
                return news
        except Exception as e:
            logger.warning(f"News fetch failed {sym}: {e}")
            return []

    async def get_market_news(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Aggregate top market news across Nifty movers."""
        # Use a small sample to avoid Yahoo rate limit
        sample = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "^NSEI"]
        tasks = [self.get_symbol_news(s, limit=3) for s in sample]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_news: List[Dict] = []
        for r in results:
            if isinstance(r, list):
                all_news.extend(r)
        # Deduplicate by title
        seen = set()
        deduped = []
        for n in all_news:
            if n["title"] not in seen:
                seen.add(n["title"])
                deduped.append(n)
        return deduped[:limit]

    async def get_newsapi_headlines(self, query: str = "NSE India stock market", limit: int = 8) -> List[Dict]:
        """Optional: NewsAPI.org (if NEWSAPI_KEY is set). Domain allow-listed."""
        if not self.newsapi_key:
            return []
        query = _sanitize_text(query, 120)
        url = "https://newsapi.org/v2/everything"
        params = {"q": query, "language": "en", "sortBy": "publishedAt", "pageSize": min(limit, 10)}
        headers = {"X-Api-Key": self.newsapi_key}
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(url, params=params, headers=headers)
                if resp.status_code != 200:
                    return []
                data = resp.json()
                arts = data.get("articles", [])[:limit]
                return [
                    {
                        "title": _sanitize_text(a.get("title", ""), 200),
                        "publisher": _sanitize_text(a.get("source", {}).get("name", ""), 80),
                        "link": a.get("url", "")[:500],
                        "published_at": a.get("publishedAt"),
                    }
                    for a in arts
                ]
        except Exception as e:
            logger.debug(f"NewsAPI failed: {e}")
            return []

    # ─── Sentiment ────────────────────────────────────────────────

    def _rule_sentiment(self, titles: List[str]) -> Dict[str, Any]:
        """Fallback keyword sentiment when AI is unavailable."""
        text = " ".join(t.lower() for t in titles)
        bull = sum(1 for w in _BULLISH_KW if w in text)
        bear = sum(1 for w in _BEARISH_KW if w in text)
        total = bull + bear + 1
        score = (bull - bear) / total  # -1 .. 1
        if score > 0.15:
            label = "BULLISH"
        elif score < -0.15:
            label = "BEARISH"
        else:
            label = "NEUTRAL"
        return {
            "sentiment": label,
            "confidence": int(abs(score) * 100),
            "score": round(score, 2),
            "method": "rule-based",
            "bull_hits": bull,
            "bear_hits": bear,
            "titles_analyzed": len(titles),
        }

    async def analyze_sentiment(
        self, symbols: Optional[List[str]] = None, use_ai: bool = True
    ) -> Dict[str, Any]:
        """
        Aggregate sentiment for given symbols (or market) via AI if available,
        else rule-based. Cached 2 min.
        """
        symbols = symbols or ["MARKET"]
        # Validate + normalize
        clean_syms = []
        for s in symbols[:10]:
            try:
                clean_syms.append(_validate_symbol(s))
            except ValueError:
                continue
        if not clean_syms:
            clean_syms = ["MARKET"]

        cache_key = f"sent:{','.join(sorted(clean_syms))}"
        if cache_key in _sentiment_cache:
            return _sentiment_cache[cache_key]

        # Gather titles
        all_titles: List[str] = []
        if clean_syms == ["MARKET"]:
            news = await self.get_market_news(limit=10)
        else:
            # Per-symbol
            tasks = [self.get_symbol_news(s, limit=5) for s in clean_syms]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            news = []
            for r in results:
                if isinstance(r, list):
                    news.extend(r)
        all_titles = [n["title"] for n in news if n.get("title")]
        if not all_titles:
            result = {"sentiment": "NEUTRAL", "confidence": 0, "method": "no-news", "titles_analyzed": 0}
            _sentiment_cache[cache_key] = result
            return result

        # Try AI
        if use_ai:
            try:
                from ai_agent.router import ai_router

                # Truncate + sanitize titles for prompt injection safety
                titles_block = "\n".join(f"- {_sanitize_text(t,120)}" for t in all_titles[:10])
                prompt = (
                    "You are a financial sentiment analyzer for Indian stock market (NSE).\n"
                    f"Headlines for {','.join(clean_syms)}:\n{titles_block}\n\n"
                    "Classify overall sentiment as BULLISH/BEARISH/NEUTRAL with confidence 0-100.\n"
                    'Respond ONLY as JSON: {"sentiment":"BULLISH|BEARISH|NEUTRAL","confidence":0-100,"reasoning":"...","key_drivers":["..."]}'
                )
                ai_res = await ai_router.analyze(prompt, temperature=0.2)
                if ai_res and ai_res.get("sentiment") in ("BULLISH", "BEARISH", "NEUTRAL"):
                    result = {
                        "sentiment": ai_res["sentiment"],
                        "confidence": int(ai_res.get("confidence", 60)),
                        "reasoning": _sanitize_text(str(ai_res.get("reasoning", "")), 500),
                        "key_drivers": ai_res.get("key_drivers", [])[:5],
                        "method": f"ai:{ai_res.get('_provider','unknown')}",
                        "titles_analyzed": len(all_titles),
                        "sample_titles": all_titles[:5],
                    }
                    _sentiment_cache[cache_key] = result
                    return result
            except Exception as e:
                logger.debug(f"AI sentiment failed, fallback to rule: {e}")

        # Fallback
        result = self._rule_sentiment(all_titles)
        result["sample_titles"] = all_titles[:5]
        _sentiment_cache[cache_key] = result
        return result

    async def get_symbol_sentiment(self, symbol: str) -> Dict[str, Any]:
        sym = _validate_symbol(symbol)
        return await self.analyze_sentiment(symbols=[sym])

    async def get_market_sentiment(self) -> Dict[str, Any]:
        return await self.analyze_sentiment(symbols=["MARKET"])


# Singleton
news_fetcher = NewsFetcher()
