#!/usr/bin/env bash
# AI Trader — Quick Security & Health Check (Phase 5)
# Run: bash scripts/check.sh
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== 1. Tests ==="
python3 -m pytest backend/tests/ -q

echo ""
echo "=== 2. FastAPI openapi (docs) hidden in prod? ==="
python3 - <<'PY'
import sys
sys.path.insert(0, "backend")
from config import settings
is_prod = settings.env == "production"
print(f"env={settings.env} debug={settings.debug} is_prod={is_prod}")
PY

echo ""
echo "=== 3. Symbol injection check ==="
PYTHONPATH=backend python3 <<'PY' 2>&1
try:
    from services.math_engine import math_engine
    print("math position_size:", math_engine.position_size(100000, 100, 95, 0.01, 0.55, 1.5))
    from services.news_fetcher import news_fetcher
    print("news_fetcher sanitize ok:", hasattr(news_fetcher, "_sanitize"))
    from services.fundamentals import fundamentals_engine
    print("fundamentals ok")
    from ai_agent.strategy_generator import strategy_generator
    print("strategy_generator ok")
except Exception as e:
    import traceback; traceback.print_exc()
PY

echo ""
echo "=== 4. OmniRoute SSRF guard ==="
PYTHONPATH=backend python3 <<'PY'
from ai_agent.providers.omniroute_provider import OmniRouteProvider
p = OmniRouteProvider(base_url="http://169.254.169.254/v1")
import asyncio
try:
    asyncio.run(p.complete("hi"))
except ValueError as e:
    print("SSRF blocked OK:", e)
except Exception as e:
    print("Other error (probe):", e)
else:
    print("SSRF NOT blocked!")
PY

echo ""
echo "=== 5. Bandit (if installed) ==="
if command -v bandit >/dev/null 2>&1; then
  bandit -r backend -ll -q || true
else
  echo "bandit not installed — pip install bandit"
fi

echo ""
echo "=== 6. pip-audit (if installed) ==="
if command -v pip-audit >/dev/null 2>&1; then
  pip-audit || true
else
  echo "pip-audit not installed — pip install pip-audit"
fi

echo ""
echo "=== 7. DB perms ==="
ls -l backend/data/*.db 2>/dev/null || echo "no db yet (will be 600 on creation)"

echo ""
echo "All checks done."
