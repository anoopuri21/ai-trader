"""
API Dependencies — Auth & Common Guards

Provides optional API-key auth:
  - If `ARTH_API_KEY` env is empty -> open (dev, no auth)
  - If set -> clients must send `X-API-Key: <key>` or `Authorization: Bearer <key>`

Usage:
  from api.deps import verify_api_key_optional, verify_api_key_required

  @router.post("/open", dependencies=[Depends(verify_api_key_required)])

Security: uses hmac.compare_digest to avoid timing attack.
"""

import hmac
import logging
from typing import Optional

from fastapi import Header, HTTPException, Request, Depends

logger = logging.getLogger(__name__)


def _get_expected_key() -> Optional[str]:
    try:
        from config import settings

        key = getattr(settings, "arth_api_key", None) or getattr(settings, "api_key", None)
        # Also check generic env via settings
        if not key:
            import os

            key = os.getenv("ARTH_API_KEY") or os.getenv("API_KEY")
        if key and key.strip():
            return key.strip()
        return None
    except Exception:
        return None


async def verify_api_key_optional(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None),
) -> Optional[str]:
    """
    Optional auth: if ARTH_API_KEY is not set, allow all.
    If set, require valid key via X-API-Key or Bearer token.
    Returns the validated key or None (when open).
    """
    expected = _get_expected_key()
    if not expected:
        return None  # open mode (dev)

    # Extract provided key
    provided = None
    if x_api_key and x_api_key.strip():
        provided = x_api_key.strip()
    elif authorization and authorization.lower().startswith("bearer "):
        provided = authorization[7:].strip()

    # Also allow ?api_key= query for websocket/browser
    if not provided:
        provided = request.query_params.get("api_key") or request.query_params.get("token")

    if not provided:
        raise HTTPException(status_code=401, detail="Missing API key. Send X-API-Key header or Bearer token.")

    # Constant-time compare
    if not hmac.compare_digest(provided, expected):
        logger.warning(f"Invalid API key attempt from {request.client.host if request.client else 'unknown'}")
        raise HTTPException(status_code=401, detail="Invalid API key.")

    return provided


async def verify_api_key_required(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None),
) -> str:
    """Strict version — always requires key if expected is set, else open as well but documents intent."""
    result = await verify_api_key_optional(request, x_api_key, authorization)
    expected = _get_expected_key()
    if expected and not result:
        raise HTTPException(status_code=401, detail="API key required")
    # When open mode, return a placeholder
    return result or "open"


# For routes that should be public but want to know if request is authed
async def get_optional_user(request: Request) -> Optional[str]:
    try:
        return await verify_api_key_optional(request, None, None)
    except HTTPException:
        return None
