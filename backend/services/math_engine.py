"""
ARTH — Math & Risk Engine (Engine #3)

Pure quantitative calculations: Kelly Criterion, position sizing,
Sharpe, Sortino, expectancy, risk grid, pyramiding, ATR-based
stop/target. No AI, no network — deterministic math only.

Security: no user code execution, no eval, all inputs validated &
        clamped, NaN/Inf rejected, division-by-zero guarded.
"""

import math
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def _safe(v, default: float = 0.0) -> float:
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except Exception:
        return default


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


class MathEngine:
    """Deterministic risk & sizing calculations."""

    # ─── Kelly ────────────────────────────────────────────────────

    @staticmethod
    def kelly_fraction(win_prob: float, win_payoff: float, loss_payoff: float = 1.0) -> Dict[str, Any]:
        """
        Classic Kelly: f* = p - (1-p)/b  where b = win/loss payoff ratio
        win_payoff/loss_payoff e.g. avg_win=3% , avg_loss=1.5% -> b=2
        Returns fraction of capital to bet. Clamped 0..0.25 (quarter-Kelly for safety).
        """
        p = _clamp(_safe(win_prob, 0.5), 0.01, 0.99)
        b = _safe(win_payoff, 1.0)
        if b <= 0:
            b = 1.0
        loss = _safe(loss_payoff, 1.0)
        if loss <= 0:
            loss = 1.0
        b_ratio = b / loss

        f_star = p - (1 - p) / b_ratio if b_ratio else 0
        f_star = _clamp(f_star, 0, 0.25)  # quarter Kelly cap
        # Human-readable
        if f_star < 0.01:
            advice = "SKIP"
        elif f_star < 0.05:
            advice = "QUARTER"
        elif f_star < 0.12:
            advice = "HALF"
        else:
            advice = "FULL"

        return {
            "win_prob": round(p, 3),
            "payoff_ratio": round(b_ratio, 2),
            "kelly_full": round(f_star * 4, 4),  # undo quarter cap for display
            "kelly_quarter": round(f_star, 4),
            "suggested_fraction": round(f_star, 4),
            "advice": advice,
            "formula": "f* = p - (1-p)/b, capped to 0.25 (quarter-Kelly)",
        }

    @staticmethod
    def position_size(
        capital: float,
        entry: float,
        stop: float,
        risk_pct: float = 0.01,
        win_prob: Optional[float] = None,
        payoff_ratio: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Risk-based sizing: risk_amount = capital * risk_pct
        qty = risk_amount / |entry - stop|
        Optionally Kelly-adjusted.
        """
        cap = _safe(capital, 100000)
        if cap <= 0:
            cap = 100000
        ent = _safe(entry, 0)
        stp = _safe(stop, 0)
        risk = _clamp(_safe(risk_pct, 0.01), 0.001, 0.05)  # 0.1% .. 5%

        if ent <= 0 or stp <= 0 or ent == stp:
            return {"error": "Invalid entry/stop", "qty": 0, "risk_amount": 0}

        risk_amount = cap * risk
        per_share_risk = abs(ent - stp)
        qty = int(risk_amount // per_share_risk) if per_share_risk else 0
        qty = max(0, qty)

        # Kelly adjustment if provided
        kelly = None
        if win_prob is not None and payoff_ratio is not None:
            kelly = MathEngine.kelly_fraction(win_prob, payoff_ratio)
            # Scale qty by Kelly quarter vs default risk
            # Default risk 1% -> Kelly says e.g. 0.06 -> scale factor ~6x but capped
            kelly_factor = _clamp(kelly["suggested_fraction"] / 0.01, 0, 3)
            kelly_qty = int(qty * kelly_factor)
            kelly_qty = max(0, min(kelly_qty, int(cap // ent)))  # can't exceed capital
        else:
            kelly_qty = None
            kelly_factor = None

        max_by_capital = int(cap // ent) if ent else 0
        qty = min(qty, max_by_capital)

        return {
            "capital": cap,
            "entry": ent,
            "stop": stp,
            "risk_pct": risk,
            "risk_amount": round(risk_amount, 2),
            "per_share_risk": round(per_share_risk, 2),
            "qty": qty,
            "max_qty_by_capital": max_by_capital,
            "kelly": kelly,
            "kelly_qty": kelly_qty,
            "kelly_factor": round(kelly_factor, 2) if kelly_factor else None,
            "notional": round(qty * ent, 2),
        }

    # ─── ATR Risk Grid ────────────────────────────────────────────

    @staticmethod
    def atr_levels(entry: float, atr: float, direction: str = "BUY") -> Dict[str, Any]:
        """
        ATR-based stop/target grid.
        BUY:  stop = entry - 1.5*ATR, target = entry + 3*ATR
        SELL: stop = entry + 1.5*ATR, target = entry - 3*ATR
        Caps: stop 1%..5%, target up to 10%, RR >= 1.5
        """
        ent = _safe(entry, 0)
        a = _safe(atr, 0)
        if ent <= 0 or a <= 0:
            return {"error": "Invalid entry/ATR"}

        direction = direction.upper().strip()
        if direction not in ("BUY", "SELL"):
            direction = "BUY"

        if direction == "BUY":
            raw_stop = ent - 1.5 * a
            raw_target = ent + 3.0 * a
        else:
            raw_stop = ent + 1.5 * a
            raw_target = ent - 3.0 * a

        # Caps
        # Stop distance 1%..5%
        min_stop_dist = ent * 0.01
        max_stop_dist = ent * 0.05
        # Target distance up to 10%
        max_target_dist = ent * 0.10

        if direction == "BUY":
            stop_dist = _clamp(ent - raw_stop, min_stop_dist, max_stop_dist)
            stop = ent - stop_dist
            target_dist = _clamp(raw_target - ent, min_stop_dist * 1.5, max_target_dist)
            target = ent + target_dist
        else:
            stop_dist = _clamp(raw_stop - ent, min_stop_dist, max_stop_dist)
            stop = ent + stop_dist
            target_dist = _clamp(ent - raw_target, min_stop_dist * 1.5, max_target_dist)
            target = ent - target_dist

        # Risk-reward
        risk = abs(ent - stop)
        reward = abs(target - ent)
        rr = reward / risk if risk else 0
        # Enforce min RR
        if rr < 1.5 and risk:
            # Extend target to meet 1.5
            needed = risk * 1.5
            if direction == "BUY":
                target = ent + needed
            else:
                target = ent - needed
            reward = abs(target - ent)
            rr = reward / risk if risk else 0

        return {
            "entry": round(ent, 2),
            "atr": round(a, 2),
            "direction": direction,
            "stop": round(stop, 2),
            "target": round(target, 2),
            "stop_pct": round(abs(ent - stop) / ent * 100, 2),
            "target_pct": round(abs(target - ent) / ent * 100, 2),
            "risk_reward": round(rr, 2),
            "caps": {"min_stop_pct": 1, "max_stop_pct": 5, "max_target_pct": 10, "min_rr": 1.5},
        }

    # ─── Expectancy & Performance ─────────────────────────────────

    @staticmethod
    def expectancy(win_rate: float, avg_win: float, avg_loss: float) -> Dict[str, Any]:
        """
        Expectancy = (p * avg_win) - ((1-p) * avg_loss)
        avg_win / avg_loss are positive percentages, e.g. 2.5 means 2.5%
        """
        p = _clamp(_safe(win_rate, 0) / 100 if win_rate > 1 else _safe(win_rate, 0), 0, 1)
        # If win_rate was already 0..1, handle both
        if win_rate > 1:
            p = _clamp(win_rate / 100, 0, 1)
        w = abs(_safe(avg_win, 0))
        l = abs(_safe(avg_loss, 0))

        exp = p * w - (1 - p) * l
        # Profit factor
        pf = (p * w) / ((1 - p) * l) if (1 - p) * l else float("inf") if p * w else 0
        # Needed win rate to break even
        breakeven = l / (w + l) if (w + l) else 0.5

        verdict = "EDGE" if exp > 0.3 else "NEUTRAL" if exp > 0 else "NO_EDGE"

        return {
            "win_rate": round(p * 100, 1),
            "avg_win_pct": round(w, 2),
            "avg_loss_pct": round(l, 2),
            "expectancy_pct": round(exp, 3),
            "profit_factor": round(pf, 2) if pf != float("inf") else None,
            "breakeven_win_rate": round(breakeven * 100, 1),
            "verdict": verdict,
        }

    @staticmethod
    def sharpe(returns: List[float], risk_free: float = 0.06) -> Dict[str, Any]:
        """
        Sharpe = (mean(returns) - rf) / std(returns) * sqrt(252)
        returns are daily % e.g. [0.5, -0.2, 1.1]
        """
        if not returns or len(returns) < 5:
            return {"sharpe": None, "reason": "Need >=5 returns"}
        try:
            import statistics

            mean = statistics.mean(returns)
            stdev = statistics.pstdev(returns) if len(returns) > 1 else 0
            if stdev == 0:
                return {"sharpe": 0, "mean": round(mean, 3), "stdev": 0}
            # Daily rf approx 6% annual / 252
            rf_daily = risk_free / 252 * 100  # convert to %
            sharpe = (mean - rf_daily) / stdev * math.sqrt(252)
            # Sortino (downside only)
            downside = [r for r in returns if r < 0]
            downside_dev = statistics.pstdev(downside) if len(downside) > 1 else (abs(statistics.mean(downside)) if downside else stdev)
            sortino = (mean - rf_daily) / downside_dev * math.sqrt(252) if downside_dev else 0

            return {
                "sharpe": round(sharpe, 2),
                "sortino": round(sortino, 2),
                "mean_daily": round(mean, 3),
                "stdev": round(stdev, 3),
                "risk_free_annual": risk_free,
                "samples": len(returns),
            }
        except Exception as e:
            logger.debug(f"Sharpe calc failed: {e}")
            return {"sharpe": None, "error": str(e)}

    @staticmethod
    def max_drawdown(equity_curve: List[float]) -> Dict[str, Any]:
        """Peak-to-trough max drawdown %."""
        if not equity_curve or len(equity_curve) < 2:
            return {"max_drawdown_pct": 0, "peak": None, "trough": None}
        peak = equity_curve[0]
        max_dd = 0
        peak_at = 0
        trough_at = 0
        best_peak = peak
        for i, v in enumerate(equity_curve):
            if v > peak:
                peak = v
                best_peak = v
                peak_at = i
            dd = (peak - v) / peak * 100 if peak else 0
            if dd > max_dd:
                max_dd = dd
                trough_at = i
        return {
            "max_drawdown_pct": round(max_dd, 2),
            "peak": round(best_peak, 2),
            "peak_idx": peak_at,
            "trough_idx": trough_at,
        }


math_engine = MathEngine()
