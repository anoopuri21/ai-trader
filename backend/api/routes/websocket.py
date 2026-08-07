"""
WebSocket endpoint for real-time signal updates
"""

import asyncio
import json
import logging
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


@router.websocket("/ws/signals")
async def websocket_signals(websocket: WebSocket):
    """Real-time signal updates via WebSocket"""
    await manager.connect(websocket)
    
    try:
        while True:
            # Send periodic updates every 30 seconds
            try:
                from services.price_fetcher import price_fetcher
                from services.signal_generator import signal_generator
                from models.stock import NIFTY_50_SYMBOLS
                
                # Get a few top signals
                import random
                sample_symbols = random.sample(NIFTY_50_SYMBOLS, min(5, len(NIFTY_50_SYMBOLS)))
                
                signals_data = []
                for symbol in sample_symbols:
                    signal = await signal_generator.generate_signal(symbol)
                    if signal:
                        signals_data.append({
                            "symbol": signal.stock.symbol,
                            "price": signal.stock.current_price,
                            "change_percent": signal.stock.change_percent,
                            "signal": signal.signal.value,
                            "confidence": signal.confidence,
                            "rsi": signal.indicators.rsi,
                        })
                
                await websocket.send_json({
                    "type": "signals_update",
                    "timestamp": datetime.utcnow().isoformat(),
                    "signals": signals_data,
                })
            
            except Exception as e:
                logger.error(f"WebSocket broadcast error: {e}")
            
            # Wait 30 seconds
            await asyncio.sleep(30)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.websocket("/ws/arth")
async def websocket_arth(websocket: WebSocket):
    """Real-time ARTH updates via WebSocket"""
    await manager.connect(websocket)
    
    try:
        while True:
            try:
                from ai_agent.arth import arth
                
                if arth.brain:
                    stats = arth.brain.get_stats()
                    await websocket.send_json({
                        "type": "arth_update",
                        "timestamp": datetime.utcnow().isoformat(),
                        "status": arth.status,
                        "brain_stats": stats,
                    })
            
            except Exception as e:
                logger.error(f"ARTH WebSocket error: {e}")
            
            await asyncio.sleep(60)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"ARTH WebSocket error: {e}")
        manager.disconnect(websocket)
