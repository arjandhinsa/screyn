"""
WebSocket endpoint — streams live metrics to connected clients.

Payload shape: see LiveFrame in schemas/session.py.
One broadcast per METRIC_INTERVAL_SECONDS (default 5s).
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.session_manager import session_manager

router = APIRouter()


@router.websocket("/ws/live")
async def live_metrics(ws: WebSocket):
    await session_manager.subscribe(ws)
    try:
        while True:
            # We don't expect client → server messages, but keep the connection
            # alive and listen for pings / disconnect signals.
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        session_manager.unsubscribe(ws)
