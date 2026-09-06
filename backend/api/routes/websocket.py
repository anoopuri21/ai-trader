"""
WebSocket endpoint for real-time signal updates — hardened

Fixes V-03: max connections, auth, heartbeat, safe disconnect
"""

import asyncio
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """Manage WebSocket connections with limits and safe disconnect."""

    def __init__(self, max_connections: int = 100):
        self.active_connections: list[WebSocket] = []
        self.max_connections = max_connections
        # Per-IP counter
        self._per_ip: dict[str, int] = {}

    def _get_max(self) -> int:
        try:
            from config import settings

            return getattr(settings, "max_ws_connections", self.max_connections)
        except Exception:
            return self.max_connections

    async def connect(self, websocket: WebSocket) -> bool:
        # Check max
        if len(self.active_connections) >= self._get_max():
            await websocket.close(code=1013, reason="Server overloaded, max connections reached")
            logger.warning(f"WebSocket rejected: max {self._get_max()} reached")
            return False

        # Per-IP limit 5
        ip = websocket.client.host if websocket.client else "unknown"
        if self._per_ip.get(ip, 0) >= 5:
            await websocket.close(code=1013, reason="Too many connections from your IP")
            logger.warning(f"WebSocket rejected: per-IP limit for {ip}")
            return False

        # Optional auth if ARTH_API_KEY is set
        try:
            from api.deps import _get_expected_key

            expected = _get_expected_key()
            if expected:
                token = websocket.query_params.get("token") or websocket.query_params.get("api_key")
                # Also check header via websocket.headers
                if not token:
                    token = websocket.headers.get("x-api-key") or websocket.headers.get("authorization", "").replace("Bearer ", "")
                import hmac

                if not token or not hmac.compare_digest(token.strip(), expected):
                    await websocket.close(code=1008, reason="Unauthorized")
                    logger.warning(f"WebSocket unauthorized from {ip}")
                    return False
        except Exception:
            pass

        await websocket.accept()
        self.active_connections.append(websocket)
        self._per_ip[ip] = self._per_ip.get(ip, 0) + 1
        logger.info(f"WebSocket connected {ip}. Total: {len(self.active_connections)}")
        return True

    def disconnect(self, websocket: WebSocket):
        try:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
                ip = websocket.client.host if websocket.client else "unknown"
                if ip in self._per_ip:
                    self._per_ip[ip] = max(0, self._per_ip[ip] - 1)
                    if self._per_ip[ip] == 0:
                        del self._per_ip[ip]
                logger.info(f"WebSocket disconnected {ip}. Total: {len(self.active_connections)}")
        except ValueError:
            pass  # already removed
        except Exception as e:
            logger.debug(f"WebSocket disconnect error: {e}")

    async def broadcast(self, message: dict):
        for ws in list(self.active_connections):
            try:
                await ws.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


@router.websocket("/ws/signals")
async def websocket_signals(websocket: WebSocket):
    """Real-time signal updates — 30s heartbeat, pong handling"""
    if not await manager.connect(websocket):
        return

    try:
        while True:
            try:
                # Heartbeat ping
                try:
                    await websocket.send_json({"type": "ping", "ts": datetime.now(timezone.utc).isoformat()})
                except Exception:
                    break  # client gone

                from services.price_fetcher import price_fetcher
                from services.signal_generator import signal_generator
                from models.stock import NIFTY_50_SYMBOLS
                import random

                sample_symbols = random.sample(NIFTY_50_SYMBOLS, min(5, len(NIFTY_50_SYMBOLS)))
                signals_data = []
                for symbol in sample_symbols:
                    try:
                        signal = await signal_generator.generate_signal(symbol)
                        if signal:
                            signals_data.append(
                                {
                                    "symbol": signal.stock.symbol,
                                    "price": signal.stock.current_price,
                                    "change_percent": signal.stock.change_percent,
                                    "signal": signal.signal.value,
                                    "confidence": signal.confidence,
                                    "rsi": signal.indicators.rsi,
                                }
                            )
                    except Exception as e:
                        logger.debug(f"WS signal {symbol} error: {e}")

                try:
                    await websocket.send_json(
                        {
                            "type": "signals_update",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "signals": signals_data,
                        }
                    )
                except Exception:
                    break

                # Wait 30s or until client ping/pong
                try:
                    await asyncio.wait_for(websocket.receive_text(), timeout=30)
                    # If client sends anything, treat as pong/keepalive
                except asyncio.TimeoutError:
                    pass
                except WebSocketDisconnect:
                    break
            except Exception as e:
                logger.error(f"WebSocket broadcast error: {e}")
                await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)


@router.websocket("/ws/arth")
async def websocket_arth(websocket: WebSocket):
    """Real-time ARTH updates — 60s interval"""
    if not await manager.connect(websocket):
        return

    try:
        while True:
            try:
                from ai_agent.arth import arth

                if arth.brain:
                    stats = arth.brain.get_stats()
                    # Hide detailed stats if not debug (privacy)
                    try:
                        from config import settings

                        is_debug = getattr(settings, "debug", False)
                    except Exception:
                        is_debug = True
                    if not is_debug:
                        stats = {"total_predictions": stats.get("total_predictions", 0), "overall_accuracy": stats.get("overall_accuracy", 0)}
                    await websocket.send_json(
                        {
                            "type": "arth_update",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "status": arth.status,
                            "brain_stats": stats,
                        }
                    )
            except Exception as e:
                logger.debug(f"ARTH WS error: {e}")

            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=60)
            except asyncio.TimeoutError:
                pass
            except WebSocketDisconnect:
                break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"ARTH WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)
