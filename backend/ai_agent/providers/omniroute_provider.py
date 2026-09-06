"""
OmniRoute AI Provider - Unified Gateway to 356 AI Providers
Uses OpenAI-compatible API via OmniRoute gateway (https://github.com/diegosouzapw/OmniRoute)

OmniRoute aggregates 356 providers (150+ free tiers, ~1.47B tokens/mo free)
behind a single OpenAI-compatible endpoint. By pointing AI Trader at OmniRoute,
ARTH automatically gets fallback across all configured providers with 19 routing
strategies (priority, auto, lkgp, cost-optimized, etc.) and built-in resilience.

Default local endpoint: http://localhost:20128/v1
Docker / production:   http://omniroute:20128/v1  or  https://your-omniroute.host/v1

Reference: https://github.com/diegosouzapw/OmniRoute
Docs:     /tmp/OmniRoute/docs  (cloned reference)
"""

import json
import logging
import re
from typing import Optional, Dict, Any

import httpx

logger = logging.getLogger(__name__)


class OmniRouteProvider:
    """OmniRoute — unified gateway provider (OpenAI-compatible)."""

    PROVIDER_NAME = "omniroute"
    # Default model "auto" = OmniRoute's Auto-Combo (16-factor live scoring)
    # Alternatives: auto/fast, auto/cheap, auto/smart, auto/coding, auto/offline
    DEFAULT_MODEL = "auto"
    DEFAULT_BASE_URL = "http://localhost:20128/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 90,
    ):
        # Resolve from explicit args → settings → defaults
        # Settings are imported lazily to avoid circular imports at module load
        try:
            from config import settings

            _api_key = api_key if api_key is not None else getattr(settings, "omniroute_api_key", None)
            _base_url = base_url if base_url is not None else getattr(settings, "omniroute_base_url", None)
            _model = model if model is not None else getattr(settings, "omniroute_model", None)
            _timeout = getattr(settings, "omniroute_timeout", timeout)
        except Exception:
            _api_key = api_key
            _base_url = base_url
            _model = model
            _timeout = timeout

        self.api_key: Optional[str] = _api_key or None
        # Normalize base_url: strip trailing slash, ensure /v1 suffix
        raw_url = (_base_url or self.DEFAULT_BASE_URL).strip().rstrip("/")
        if not raw_url.endswith("/v1"):
            # Accept bare host:port e.g. http://localhost:20128
            if raw_url.endswith("/v1/chat/completions"):
                raw_url = raw_url[: -len("/chat/completions")]
            elif "/v1" not in raw_url:
                raw_url = raw_url + "/v1"
        self.base_url: str = raw_url
        self.model: str = _model or self.DEFAULT_MODEL
        self.timeout: int = _timeout
        self.available: bool = False

        self._initialize()

    def _initialize(self):
        """Determine availability. OmniRoute can run without API key when REQUIRE_API_KEY=false."""
        # Available if either an API key is configured OR the base_url is explicitly set
        # (local dev often runs without auth). We do NOT fail if gateway is offline at import;
        # that is checked lazily at request time with fallback.
        if self.api_key:
            self.available = True
            logger.info(f"OmniRoute provider initialized — model={self.model} base={self.base_url} (with API key)")
        else:
            # Allow keyless local gateway; still mark available so router will try it
            # If gateway is not running, analyze() will fail gracefully and fallback.
            self.available = True
            logger.info(
                f"OmniRoute provider initialized — model={self.model} base={self.base_url} (no API key, keyless mode)"
            )

        # Optional: warn if neither key nor custom URL? Still available for local default.
        if not self.api_key and self.base_url == self.DEFAULT_BASE_URL:
            logger.debug("OmniRoute: No API key configured — trying keyless local gateway at %s", self.base_url)

    async def analyze(self, prompt: str, temperature: float = 0.3) -> Optional[Dict[str, Any]]:
        """Send analysis request via OmniRoute OpenAI-compatible endpoint."""
        if not self.available:
            return None

        # Build headers — Bearer token is optional when gateway runs with REQUIRE_API_KEY=false
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            # Some gateways accept dummy key; send placeholder to satisfy OpenAI SDK checks
            headers["Authorization"] = "Bearer omniroute-keyless"

        # OmniRoute supports standard OpenAI chat/completions params plus custom headers:
        # X-OmniRoute-No-Cache, X-Session-Id etc. We request JSON object if model supports it.
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are ARTH, an expert AI trading analyst for Indian stock markets (NSE). Always respond with valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": 2000,
        }

        # Try with response_format first (supported by many models via OmniRoute)
        # If the model rejects it, we retry without it.
        for attempt, use_json_mode in enumerate([(True, "json_object"), (False, None)] if True else []):
            # First attempt with json_object, second without
            if attempt == 0:
                payload["response_format"] = {"type": "json_object"}
            else:
                payload.pop("response_format", None)
                logger.debug("OmniRoute: retrying without response_format")

            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    url = f"{self.base_url}/chat/completions"
                    logger.debug(f"OmniRoute: POST {url} model={self.model} attempt={attempt+1}")
                    response = await client.post(url, headers=headers, json=payload)

                    if response.status_code == 401:
                        logger.warning("OmniRoute: 401 Unauthorized — check OMNIROUTE_API_KEY")
                        if attempt == 0:
                            continue
                        return None
                    if response.status_code == 404 and attempt == 0:
                        # Some models gate response_format, retry without
                        logger.debug("OmniRoute 404 on response_format, retrying")
                        continue
                    if response.status_code == 400 and "response_format" in response.text and attempt == 0:
                        logger.debug("OmniRoute 400 response_format not supported, retrying")
                        continue
                    if response.status_code != 200:
                        logger.warning(f"OmniRoute HTTP {response.status_code}: {response.text[:500]}")
                        if attempt == 0 and response.status_code in (400, 422):
                            continue
                        return None

                    data = response.json()
                    # OpenAI shape: choices[0].message.content
                    choices = data.get("choices", [])
                    if not choices:
                        logger.warning(f"OmniRoute: empty choices {data}")
                        return None

                    content = choices[0].get("message", {}).get("content", "")
                    if not content:
                        # Some providers via OmniRoute may put content in reasoning field
                        content = choices[0].get("message", {}).get("reasoning_content", "") or ""

                    if not content:
                        logger.warning("OmniRoute: empty content")
                        return None

                    # Add provider metadata to response for debugging
                    raw_provider = data.get("provider") or data.get("model") or self.model
                    x_decision = response.headers.get("X-OmniRoute-Decision", "")

                    # Try direct JSON parse
                    try:
                        parsed = json.loads(content)
                        if isinstance(parsed, dict):
                            # Attach trace
                            if x_decision:
                                parsed["_omni_decision"] = x_decision
                            return parsed
                        else:
                            return {"result": parsed, "raw_response": content}
                    except json.JSONDecodeError:
                        # Extract JSON block via regex — matches any JSON object across lines
                        m = re.search(r"\{[\s\S]*\}", content)
                        if m:
                            try:
                                parsed = json.loads(m.group())
                                if x_decision:
                                    parsed["_omni_decision"] = x_decision
                                return parsed
                            except json.JSONDecodeError:
                                pass
                        # Fallback: wrap raw text
                        logger.debug(f"OmniRoute: non-JSON response, wrapping: {content[:300]}")
                        return {"raw_response": content, "provider": self.PROVIDER_NAME, "_omni_decision": x_decision}

            except httpx.ConnectError as e:
                logger.warning(f"OmniRoute connection failed ({self.base_url}): {e} — gateway may not be running")
                return None
            except httpx.TimeoutException:
                logger.warning(f"OmniRoute timeout after {self.timeout}s")
                return None
            except Exception as e:
                logger.error(f"OmniRoute analysis error: {e}")
                if attempt == 0:
                    continue
                return None

        return None

    async def health_check(self) -> Dict[str, Any]:
        """Optional helper to probe gateway liveness (GET /v1/models)."""
        headers: Dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.base_url}/models", headers=headers)
                return {
                    "reachable": resp.status_code in (200, 401),
                    "status_code": resp.status_code,
                    "base_url": self.base_url,
                    "model": self.model,
                }
        except Exception as e:
            return {"reachable": False, "error": str(e), "base_url": self.base_url}

    def get_status(self) -> Dict[str, Any]:
        return {
            "provider": self.PROVIDER_NAME,
            "available": self.available,
            "model": self.model,
            "base_url": self.base_url,
            "speed": "fast",
            "gateway": "omniroute",
            "has_api_key": bool(self.api_key),
        }
