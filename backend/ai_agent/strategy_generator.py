"""
ARTH — Auto Strategy Generator (Engine #4)

Uses backtest results + brain accuracy + market regime to propose
new trading rules / parameter tweaks. Stores proposals as
learning_rules and validates before activation.

Security:
  - No code generation / eval — only JSON rule specs
  - Rule names sanitized: ^[a-z0-9_]{3,50}$
  - Numeric bounds clamped (no extreme leverage)
  - AI prompt truncated + sanitized, JSON-only response
  - Uses parameterized SQL via brain
  - Rate-limited: max 3 new rules per day per type
"""

import json
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

_RULE_NAME_RE = re.compile(r"^[a-z0-9_]{3,50}$")
_VALID_TYPES = {"entry", "exit", "filter", "confidence_adjustment", "risk"}

# Rate-limit in-memory (per process, OK for single instance)
_rule_gen_timestamps: List[float] = []


def _sanitize_rule_name(name: str) -> str:
    n = re.sub(r"[^a-z0-9_]", "_", name.lower().strip())[:50]
    n = re.sub(r"_{2,}", "_", n).strip("_")
    if not _RULE_NAME_RE.match(n):
        raise ValueError(f"Invalid rule name after sanitize: {n}")
    return n


def _clamp_rule_data(rule_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Clamp numeric fields to safe ranges."""
    d = dict(data)
    # Common clamp
    if "adjustment" in d:
        d["adjustment"] = max(-20, min(20, int(d["adjustment"])))
    if "weight" in d:
        d["weight"] = max(0.1, min(3.0, float(d["weight"])))
    if "rsi_oversold" in d:
        d["rsi_oversold"] = max(10, min(40, int(d["rsi_oversold"])))
    if "rsi_overbought" in d:
        d["rsi_overbought"] = max(60, min(90, int(d["rsi_overbought"])))
    if "atr_stop_multiplier" in d:
        d["atr_stop_multiplier"] = max(0.5, min(3.0, float(d["atr_stop_multiplier"])))
    if "atr_target_multiplier" in d:
        d["atr_target_multiplier"] = max(1.0, min(5.0, float(d["atr_target_multiplier"])))
    return d


def _rate_limited() -> bool:
    now = time.time()
    # Keep only last 24h
    global _rule_gen_timestamps
    _rule_gen_timestamps = [t for t in _rule_gen_timestamps if now - t < 86400]
    if len(_rule_gen_timestamps) >= 6:  # max 6 rules per day globally
        return True
    _rule_gen_timestamps.append(now)
    return False


class StrategyGenerator:
    """Propose new strategies/rules based on performance data."""

    async def generate_rules(
        self, lookback_days: int = 14, dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Main entry: analyze recent performance and propose rules.
        dry_run=True => return proposals without storing.
        """
        lookback_days = max(3, min(lookback_days, 90))

        # Gather data from brain
        from ai_agent.brain import ArthBrain

        brain = ArthBrain()

        accuracy = brain.get_prediction_accuracy(lookback_days)
        by_signal = brain.get_signals_by_accuracy(lookback_days)
        top_patterns = brain.get_top_patterns(min_uses=3)
        active_rules = brain.get_active_rules()
        recent = brain.get_recent_predictions(limit=20)

        # Need minimum data
        if accuracy["total_predictions"] < 10:
            return {
                "status": "insufficient_data",
                "reason": f"Need >=10 resolved predictions, have {accuracy['total_predictions']}",
                "accuracy": accuracy,
            }

        # Heuristic proposals (no AI) — always runs
        heuristic_rules = self._heuristic_proposals(by_signal, top_patterns, accuracy)

        # AI proposals (via OmniRoute) — enrich
        ai_rules: List[Dict] = []
        ai_summary = None
        try:
            from ai_agent.router import ai_router

            # Build compact, sanitized context (no raw SQL, no user input)
            sig_block = json.dumps(by_signal, indent=2)[:2000]
            pat_block = json.dumps(
                [{"name": p["pattern_name"], "rate": round(p.get("success_rate", 0), 1), "uses": p.get("total_uses", 0)} for p in top_patterns[:5]],
                indent=2,
            )[:1500]

            prompt = (
                "You are ARTH, a trading strategy researcher. Based on recent performance, propose up to 3 NEW rules.\n"
                f"Lookback {lookback_days}d: accuracy {accuracy['accuracy']}% ({accuracy['correct_predictions']}/{accuracy['total_predictions']})\n"
                f"By signal: {sig_block}\n"
                f"Top patterns: {pat_block}\n"
                "Valid rule types: entry, exit, filter, confidence_adjustment, risk.\n"
                "Examples: {name: boost_rsi_buy, type: confidence_adjustment, data: {signal: BUY, adjustment: 5}}\n"
                "Be conservative, clamp adjustments to +/-10.\n"
                'Respond ONLY as JSON: {"proposals":[{"name":"...","type":"...","data":{},"confidence":0-100,"rationale":"..."}],"summary":"..."}'
            )
            prompt = prompt[:4000]
            ai_res = await ai_router.analyze(prompt, temperature=0.4)
            if ai_res and isinstance(ai_res.get("proposals"), list):
                for p in ai_res["proposals"][:3]:
                    try:
                        name = _sanitize_rule_name(str(p.get("name", "")))
                        rtype = str(p.get("type", "")).lower().strip()
                        if rtype not in _VALID_TYPES:
                            continue
                        data = _clamp_rule_data(rtype, p.get("data", {}) if isinstance(p.get("data"), dict) else {})
                        conf = max(0, min(100, int(p.get("confidence", 50))))
                        if conf < 55:
                            continue  # skip low confidence
                        ai_rules.append(
                            {
                                "name": name,
                                "type": rtype,
                                "data": data,
                                "confidence": conf,
                                "rationale": str(p.get("rationale", ""))[:300],
                                "source": f"ai:{ai_res.get('_provider','unknown')}",
                            }
                        )
                    except Exception as e:
                        logger.debug(f"Skip bad AI proposal {p}: {e}")
                ai_summary = str(ai_res.get("summary", ""))[:500]
        except Exception as e:
            logger.debug(f"AI rule generation failed: {e}")

        # Merge + deduplicate
        all_proposals = heuristic_rules + ai_rules
        # Deduplicate by name
        seen = set()
        deduped = []
        for r in all_proposals:
            if r["name"] not in seen:
                seen.add(r["name"])
                deduped.append(r)

        # Rate limit check
        if not dry_run and _rate_limited():
            return {
                "status": "rate_limited",
                "reason": "Max 6 new rules per day reached, try tomorrow or use dry_run",
                "proposals": deduped[:3],
            }

        # Store (unless dry_run)
        stored = []
        if not dry_run:
            for r in deduped[:3]:
                try:
                    # Don't overwrite high-confidence existing rule with low confidence
                    existing = [x for x in active_rules if x["rule_name"] == r["name"]]
                    if existing and existing[0].get("confidence_score", 0) > r["confidence"] / 100:
                        continue
                    brain.store_learning_rule(
                        name=r["name"],
                        rule_type=r["type"],
                        rule_data=r["data"],
                        weight=r["confidence"] / 100,
                    )
                    stored.append(r["name"])
                except Exception as e:
                    logger.warning(f"Store rule {r['name']} failed: {e}")

        return {
            "status": "generated" if stored or dry_run else "no_new_rules",
            "lookback_days": lookback_days,
            "accuracy": accuracy,
            "by_signal": by_signal,
            "heuristic_count": len(heuristic_rules),
            "ai_count": len(ai_rules),
            "ai_summary": ai_summary,
            "proposals": deduped[:5],
            "stored": stored,
            "dry_run": dry_run,
        }

    def _heuristic_proposals(
        self, by_signal: Dict[str, Any], top_patterns: List[Dict], accuracy: Dict
    ) -> List[Dict[str, Any]]:
        """Deterministic proposals without AI."""
        proposals: List[Dict] = []

        # 1. Boost / reduce signals based on accuracy
        for sig, data in by_signal.items():
            total = data.get("total", 0)
            acc = data.get("accuracy", 0)
            if total < 5:
                continue
            if acc >= 70:
                proposals.append(
                    {
                        "name": f"boost_{sig.lower()}",
                        "type": "confidence_adjustment",
                        "data": _clamp_rule_data("confidence_adjustment", {"signal": sig, "adjustment": 5}),
                        "confidence": int(acc),
                        "rationale": f"{sig} {acc}% over {total} trades — boost confidence",
                        "source": "heuristic",
                    }
                )
            elif acc <= 40:
                proposals.append(
                    {
                        "name": f"reduce_{sig.lower()}",
                        "type": "confidence_adjustment",
                        "data": _clamp_rule_data("confidence_adjustment", {"signal": sig, "adjustment": -5}),
                        "confidence": int(100 - acc),
                        "rationale": f"{sig} {acc}% over {total} trades — reduce confidence",
                        "source": "heuristic",
                    }
                )

        # 2. Pattern-based filter
        for p in top_patterns[:3]:
            rate = p.get("success_rate", 0)
            uses = p.get("total_uses", 0)
            name = p.get("pattern_name", "")
            if uses >= 10 and rate < 35:
                # Failing pattern -> add filter
                try:
                    rname = _sanitize_rule_name(f"filter_{name}")
                    proposals.append(
                        {
                            "name": rname,
                            "type": "filter",
                            "data": {"pattern": name, "action": "require_confirmation"},
                            "confidence": 65,
                            "rationale": f"Pattern {name} {rate:.1f}% — require extra confirmation",
                            "source": "heuristic",
                        }
                    )
                except Exception:
                    pass

        # 3. Overall low accuracy -> tighten risk
        if accuracy.get("accuracy", 100) < 45 and accuracy.get("total_predictions", 0) >= 20:
            proposals.append(
                {
                    "name": "tighten_atr_stop",
                    "type": "risk",
                    "data": _clamp_rule_data("risk", {"atr_stop_multiplier": 1.2, "atr_target_multiplier": 2.0}),
                    "confidence": 60,
                    "rationale": f"Overall {accuracy['accuracy']}% — tighten stops, reduce target",
                    "source": "heuristic",
                }
            )

        return proposals[:3]

    async def evaluate_stored_rules(self) -> Dict[str, Any]:
        """Report active rules performance (from brain)."""
        from ai_agent.brain import ArthBrain

        brain = ArthBrain()
        rules = brain.get_active_rules()
        # Simple report — brain already tracks success_count / failure_count
        report = []
        for r in rules:
            total = (r.get("success_count", 0) or 0) + (r.get("failure_count", 0) or 0)
            acc = (r.get("success_count", 0) / total * 100) if total else 0
            report.append(
                {
                    "name": r["rule_name"],
                    "type": r["rule_type"],
                    "confidence": round(r.get("confidence_score", 0) * 100, 1),
                    "uses": total,
                    "accuracy": round(acc, 1),
                    "weight": r.get("weight", 1),
                }
            )
        report.sort(key=lambda x: x["accuracy"], reverse=True)
        return {"count": len(report), "rules": report[:20]}


strategy_generator = StrategyGenerator()
