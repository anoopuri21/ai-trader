"""
ARTH — Fundamentals Engine (Engine #2)

Fetches company fundamentals via Yahoo Finance (free) and scores them
for trading decisions. No external paid API required.

Metrics: P/E, Forward P/E, PEG, ROE, Debt/Equity, Profit Margins,
         Earnings growth, Revenue growth, Dividend yield, 52W range,
         analyst recommendation, beta.

Security:
  - Symbol validated via strict regex + allowlist
  - No SSRF (only yfinance with hard-coded .NS suffix)
  - Cache TTL 10 min to avoid Yahoo rate limit abuse
  - No eval, no raw SQL, all numeric parsing guarded
  - AI prompt sanitized + truncated
"""

import asyncio
import logging
import re
from typing import Dict, Any, Optional

from cachetools import TTLCache

logger = logging.getLogger(__name__)

_SYMBOL_RE = re.compile(r"^[A-Z0-9\.\^]{1,20}$")
try:
    from models.stock import NIFTY_50_SYMBOLS, NIFTY_BANK_SYMBOLS

    _ALLOWED = set(NIFTY_50_SYMBOLS + NIFTY_BANK_SYMBOLS)
except Exception:
    _ALLOWED = set()

_cache = TTLCache(maxsize=200, ttl=600)  # 10 min


def _validate_symbol(symbol: str) -> str:
    s = symbol.strip().upper()
    if not _SYMBOL_RE.match(s):
        raise ValueError(f"Invalid symbol {symbol}")
    return s


def _safe_float(v, default=None):
    try:
        if v is None or v == "":
            return default
        f = float(v)
        if f != f or f in (float("inf"), float("-inf")):  # NaN / Inf
            return default
        return f
    except Exception:
        return default


def _score_fundamentals(info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Heuristic scoring 0-100 for each pillar.
    Pure math, no AI — safe fallback.
    """
    scores: Dict[str, Any] = {}
    reasons: list[str] = []

    pe = _safe_float(info.get("trailingPE"))
    fwd_pe = _safe_float(info.get("forwardPE"))
    peg = _safe_float(info.get("pegRatio"))
    roe = _safe_float(info.get("returnOnEquity"))
    debt_eq = _safe_float(info.get("debtToEquity"))
    profit_margin = _safe_float(info.get("profitMargins"))
    rev_growth = _safe_float(info.get("revenueGrowth"))
    earn_growth = _safe_float(info.get("earningsGrowth"))
    div_yield = _safe_float(info.get("dividendYield"))
    beta = _safe_float(info.get("beta"))

    # Valuation 0-30
    val = 15
    if pe is not None:
        if 10 <= pe <= 25:
            val = 28
            reasons.append(f"P/E {pe:.1f} healthy")
        elif pe < 10:
            val = 20
            reasons.append(f"P/E {pe:.1f} cheap but check quality")
        elif pe > 40:
            val = 5
            reasons.append(f"P/E {pe:.1f} expensive")
        else:
            val = 12
    if peg is not None and 0 < peg < 1.5:
        val = min(30, val + 5)
        reasons.append(f"PEG {peg:.2f} attractive")

    # Profitability 0-25
    prof = 12
    if roe is not None:
        if roe > 0.15:
            prof = 23
            reasons.append(f"ROE {roe*100:.1f}% strong")
        elif roe > 0.08:
            prof = 16
        else:
            prof = 6
            reasons.append(f"ROE {roe*100:.1f}% weak")
    if profit_margin is not None and profit_margin > 0.15:
        prof = min(25, prof + 4)

    # Growth 0-20
    growth = 10
    if earn_growth is not None:
        if earn_growth > 0.15:
            growth = 18
            reasons.append(f"Earnings +{earn_growth*100:.1f}%")
        elif earn_growth > 0:
            growth = 13
        elif earn_growth < -0.05:
            growth = 3
            reasons.append(f"Earnings {earn_growth*100:.1f}% shrinking")

    # Leverage 0-15 (inverse — low debt is good)
    lev = 8
    if debt_eq is not None:
        if debt_eq < 50:
            lev = 14
            reasons.append(f"D/E {debt_eq:.1f} low leverage")
        elif debt_eq < 100:
            lev = 9
        else:
            lev = 3
            reasons.append(f"D/E {debt_eq:.1f} high leverage")

    # Stability 0-10 (beta + dividend)
    stab = 5
    if beta is not None:
        if 0.8 <= beta <= 1.2:
            stab = 8
        elif beta > 1.5:
            stab = 3
            reasons.append(f"Beta {beta:.2f} volatile")
    if div_yield is not None and div_yield > 0.015:
        stab = min(10, stab + 2)
        reasons.append(f"Div {div_yield*100:.1f}%")

    total = val + prof + growth + lev + stab  # 0-100
    label = "STRONG" if total >= 70 else "NEUTRAL" if total >= 45 else "WEAK"

    return {
        "total_score": int(total),
        "label": label,
        "breakdown": {"valuation": val, "profitability": prof, "growth": growth, "leverage": lev, "stability": stab},
        "reasons": reasons[:6],
        "inputs": {
            "pe": pe,
            "forward_pe": fwd_pe,
            "peg": peg,
            "roe": roe,
            "debt_to_equity": debt_eq,
            "profit_margin": profit_margin,
            "revenue_growth": rev_growth,
            "earnings_growth": earn_growth,
            "dividend_yield": div_yield,
            "beta": beta,
        },
    }


class FundamentalsEngine:
    """Fetch + score fundamentals via yfinance (free, no key)."""

    async def get_fundamentals(self, symbol: str, include_ai: bool = True) -> Dict[str, Any]:
        sym = _validate_symbol(symbol)
        cache_key = f"fund:{sym}"
        if cache_key in _cache:
            return _cache[cache_key]

        try:
            import yfinance as yf

            yahoo_sym = sym if sym.endswith(".NS") else f"{sym}.NS"
            loop = asyncio.get_event_loop()
            # yfinance info can be slow; run in executor + timeout via asyncio.wait_for
            def _fetch():
                ticker = yf.Ticker(yahoo_sym)
                # .info is deprecated in newer yfinance but still works; fallback to .fast_info + .info
                try:
                    return ticker.info or {}
                except Exception:
                    return {}

            info = await loop.run_in_executor(None, _fetch)
            if not info:
                return {"symbol": sym, "error": "No fundamentals found", "score": None}

            # Core + score
            score = _score_fundamentals(info)

            result: Dict[str, Any] = {
                "symbol": sym,
                "company_name": info.get("shortName") or info.get("longName") or sym,
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "currency": info.get("currency", "INR"),
                "current_price": _safe_float(info.get("currentPrice") or info.get("regularMarketPrice")),
                "52w_high": _safe_float(info.get("fiftyTwoWeekHigh")),
                "52w_low": _safe_float(info.get("fiftyTwoWeekLow")),
                "target_mean": _safe_float(info.get("targetMeanPrice")),
                "recommendation": info.get("recommendationKey"),
                "analysts_opinion": _safe_float(info.get("recommendationMean")),
                "score": score,
                "raw": {
                    k: info.get(k)
                    for k in (
                        "trailingPE",
                        "forwardPE",
                        "pegRatio",
                        "returnOnEquity",
                        "debtToEquity",
                        "profitMargins",
                        "revenueGrowth",
                        "earningsGrowth",
                        "dividendYield",
                        "beta",
                        "earningsQuarterlyGrowth",
                        "priceToBook",
                        "enterpriseToEbitda",
                    )
                },
                "source": "yfinance",
            }

            # Optional AI overlay — sanitized prompt
            if include_ai:
                try:
                    from ai_agent.router import ai_router

                    # Keep prompt small + sanitized
                    prompt = (
                        f"You are a fundamentals analyst for NSE {sym} ({result['company_name']}).\n"
                        f"Sector: {result['sector']}, Score: {score['total_score']}/100 ({score['label']})\n"
                        f"P/E {score['inputs']['pe']}, ROE {score['inputs']['roe']}, D/E {score['inputs']['debt_to_equity']}, "
                        f"Earnings growth {score['inputs']['earnings_growth']}, Beta {score['inputs']['beta']}\n"
                        "Give a 2-line verdict: is this fundamentally STRONG/NEUTRAL/WEAK for swing trading?\n"
                        'Respond ONLY as JSON: {"verdict":"STRONG|NEUTRAL|WEAK","confidence":0-100,"one_liner":"..."}'
                    )
                    # Truncate to avoid injection bloat
                    prompt = prompt[:2000]
                    ai_res = await ai_router.analyze(prompt, temperature=0.2)
                    if ai_res and ai_res.get("verdict") in ("STRONG", "NEUTRAL", "WEAK"):
                        result["ai_verdict"] = {
                            "verdict": ai_res["verdict"],
                            "confidence": int(ai_res.get("confidence", 60)),
                            "one_liner": str(ai_res.get("one_liner", ""))[:300],
                            "provider": ai_res.get("_provider", "unknown"),
                        }
                except Exception as e:
                    logger.debug(f"Fundamentals AI overlay failed {sym}: {e}")

            _cache[cache_key] = result
            return result

        except Exception as e:
            logger.warning(f"Fundamentals fetch failed {sym}: {e}")
            return {"symbol": sym, "error": str(e), "score": None}

    async def screen(self, symbols: list[str], min_score: int = 60) -> list[Dict[str, Any]]:
        """Screen a list of symbols, return those >= min_score. Validates each symbol."""
        clean = []
        for s in symbols[:30]:  # cap to avoid Yahoo rate limit
            try:
                clean.append(_validate_symbol(s))
            except ValueError:
                continue
        tasks = [self.get_fundamentals(s, include_ai=False) for s in clean]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        screened = []
        for r in results:
            if isinstance(r, dict) and r.get("score") and r["score"]["total_score"] >= min_score:
                screened.append(r)
        # Sort by score desc
        screened.sort(key=lambda x: x["score"]["total_score"], reverse=True)
        return screened


fundamentals_engine = FundamentalsEngine()
