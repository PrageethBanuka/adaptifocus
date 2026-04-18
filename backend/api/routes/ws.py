"""WebSocket endpoint for real-time extension ↔ server communication.

Protocol (JSON messages):
    Server → Client:
        {"type": "intervention", "data": {...}}   — push intervention decision
        {"type": "stats_update", "data": {...}}   — push refreshed stats
        {"type": "pong"}                          — heartbeat response

    Client → Server:
        {"type": "ping"}                          — heartbeat
        {"type": "page_changed", "data": {...}}   — notify of tab change
        {"type": "intervention_response", "data": {...}} — user responded
"""

from __future__ import annotations

import json
import asyncio
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections per user."""

    def __init__(self) -> None:
        self._connections: Dict[int, WebSocket] = {}

    async def connect(self, user_id: int, ws: WebSocket) -> None:
        await ws.accept()
        # Close any existing connection for this user
        old = self._connections.get(user_id)
        if old and old.client_state == WebSocketState.CONNECTED:
            try:
                await old.close(1000, "replaced")
            except Exception:
                pass
        self._connections[user_id] = ws

    def disconnect(self, user_id: int) -> None:
        self._connections.pop(user_id, None)

    async def send(self, user_id: int, message: dict) -> bool:
        """Send a JSON message to a connected user. Returns True if sent."""
        ws = self._connections.get(user_id)
        if ws and ws.client_state == WebSocketState.CONNECTED:
            try:
                await ws.send_json(message)
                return True
            except Exception:
                self.disconnect(user_id)
        return False

    def is_connected(self, user_id: int) -> bool:
        ws = self._connections.get(user_id)
        return ws is not None and ws.client_state == WebSocketState.CONNECTED

    @property
    def active_count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()


def _verify_ws_token(token: str) -> int | None:
    """Verify a JWT token and return the user_id, or None."""
    import jwt
    from config import JWT_SECRET, JWT_ALGORITHM
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        return int(user_id) if user_id else None
    except Exception:
        return None


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """Main WebSocket endpoint. Auth via query param: /ws?token=<jwt>"""
    token = ws.query_params.get("token")
    if not token:
        await ws.close(4001, "Missing token")
        return

    user_id = _verify_ws_token(token)
    if not user_id:
        await ws.close(4003, "Invalid token")
        return

    await manager.connect(user_id, ws)

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")

            if msg_type == "ping":
                await ws.send_json({"type": "pong", "ts": datetime.utcnow().isoformat() + "Z"})

            elif msg_type == "page_changed":
                # Could be used for real-time classification
                pass

            elif msg_type == "intervention_response":
                # Forward to intervention logging (future enhancement)
                pass

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        manager.disconnect(user_id)
