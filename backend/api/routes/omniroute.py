"""
OmniRoute Integration — Gateway Status & Proxy Routes

Provides health-check and model-listing passthrough for the configured
OmniRoute gateway (https://github.com/diegosouzapw/OmniRoute).

Not required for trading, but useful for Dashboard diagnostics:
  GET /api/omniroute/status  — gateway reachability + provider count
  GET /api/omniroute/models  — list models via gateway
  GET /api/omniroute/config  — current OmniRoute env config (masked key)
"""

import logging
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, HTTPException

from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/omniroute", tags=["OmniRoute Gateway"])


def _masked_key(key: str | None) -> str | None:
    if not key:
        return None
    if len(key) <= 8:
        return "***"
    return key[:4] + "***" + key[-4:]


@router.get("/config")
async def omniroute_config() -> Dict[str, Any]:
    """Show current OmniRoute gateway config (API key masked)."""
    return {
        "base_url": getattr(settings, "omniroute_base_url", "http://localhost:20128/v1"),
        "model": getattr(settings, "omniroute_model", "auto"),
        "timeout": getattr(settings, "omniroute_timeout", 90),
        "has_api_key": bool(getattr(settings, "omniroute_api_key", None)),
        "api_key_masked": _masked_key(getattr(settings, "omniroute_api_key", None)),
        "ai_priority": getattr(settings, "ai_priority", "omniroute,groq,cohere,huggingface,ollama"),
        "gateway_reference": "https://github.com/diegosouzapw/OmniRoute",
    }


@router.get("/status")
async def omniroute_status() -> Dict[str, Any]:
    """Probe OmniRoute gateway liveness (GET {base_url}/models)."""
    base_url = getattr(settings, "omniroute_base_url", "http://localhost:20128/v1").rstrip("/")
    api_key = getattr(settings, "omniroute_api_key", None)
    headers: Dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Try /models
    url = f"{base_url}/models"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
            body: Any = None
            try:
                body = resp.json()
            except Exception:
                body = resp.text[:2000]

            # 401 means gateway is up but key required — still reachable
            reachable = resp.status_code in (200, 401)
            models = []
            if isinstance(body, dict) and "data" in body:
                models = body["data"][:20]  # preview

            return {
                "reachable": reachable,
                "status_code": resp.status_code,
                "base_url": base_url,
                "models_preview": models,
                "model_count": len(body["data"]) if isinstance(body, dict) and "data" in body and isinstance(body["data"], list) else None,
                "gateway_reference": "https://github.com/diegosouzapw/OmniRoute",
                "hint": None if reachable else "Is OmniRoute running? Try: omniroute (or docker run diegosouzapw/omniroute)",
            }
    except httpx.ConnectError as e:
        return {
            "reachable": False,
            "status_code": None,
            "base_url": base_url,
            "error": f"Connection refused: {e}",
            "hint": "OmniRoute gateway not running at base_url. Start it: `omniroute` or `docker run -p 20128:20128 diegosouzapw/omniroute`",
        }
    except Exception as e:
        logger.error(f"OmniRoute status probe failed: {e}")
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/models")
async def omniroute_models() -> Dict[str, Any]:
    """List models via OmniRoute gateway (passthrough)."""
    base_url = getattr(settings, "omniroute_base_url", "http://localhost:20128/v1").rstrip("/")
    api_key = getattr(settings, "omniroute_api_key", None)
    headers: Dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    url = f"{base_url}/models"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text[:1000])
            return resp.json()
    except HTTPException:
        raise
    except httpx.ConnectError as e:
        raise HTTPException(status_code=502, detail=f"OmniRoute gateway unreachable at {base_url}: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/test")
async def omniroute_test(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Quick smoke test: send a tiny chat completion via OmniRoute.
    Body optional: {"prompt": "Say PONG", "model": "auto"}
    """
    base_url = getattr(settings, "omniroute_base_url", "http://localhost:20128/v1").rstrip("/")
    api_key = getattr(settings, "omniroute_api_key", None)
    model = (payload or {}).get("model") or getattr(settings, "omniroute_model", "auto")
    prompt = (payload or {}).get("prompt") or "Say PONG in JSON: {\"pong\": true}"

    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    else:
        headers["Authorization"] = "Bearer omniroute-keyless"

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a test assistant. Respond with valid JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 200,
    }

    url = f"{base_url}/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=headers, json=body)
            if resp.status_code != 200:
                return {
                    "success": False,
                    "status_code": resp.status_code,
                    "error": resp.text[:2000],
                    "base_url": base_url,
                    "model": model,
                }
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            decision = resp.headers.get("X-OmniRoute-Decision") or resp.headers.get("x-omniroute-decision")
            return {
                "success": True,
                "content": content,
                "decision": decision,
                "base_url": base_url,
                "model": model,
                "raw": data,
            }
    except httpx.ConnectError as e:
        return {"success": False, "error": f"Gateway unreachable: {e}", "base_url": base_url}
    except Exception as e:
        logger.error(f"OmniRoute test failed: {e}")
        return {"success": False, "error": str(e), "base_url": base_url}
