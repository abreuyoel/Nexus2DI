import logging
from typing import Dict, List, Optional
from fastapi import WebSocket, status

from app.websockets.guard import ws_guard
from app.modules.auth.entities import Usuario

logger = logging.getLogger("app.websockets")


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect_guarded(
        self, websocket: WebSocket, room: str, require_auth: bool = False
    ) -> Optional[Usuario]:
        """Validates CORS and optional JWT Auth, then accepts the WebSocket connection."""
        if not ws_guard.check_cors(websocket):
            logger.warning(f"WebSocket CORS rejection for origin: {websocket.headers.get('origin')}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="CORS Policy Violation")
            return None

        user: Optional[Usuario] = None
        if require_auth:
            user = ws_guard.authenticate(websocket)
            if not user:
                logger.warning("WebSocket Auth failure")
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
                return None

        await websocket.accept()
        if room not in self.active_connections:
            self.active_connections[room] = []
        self.active_connections[room].append(websocket)
        return user

    async def connect(self, websocket: WebSocket, room: str):
        await self.connect_guarded(websocket, room, require_auth=False)

    def disconnect(self, websocket: WebSocket, room: str):
        ws_guard.remove_limiter(websocket)
        if room in self.active_connections:
            if websocket in self.active_connections[room]:
                try:
                    self.active_connections[room].remove(websocket)
                except ValueError:
                    pass

    async def broadcast_to_room(self, room: str, message: dict):
        if room in self.active_connections:
            dead = []
            for ws in self.active_connections[room]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(ws, room)

    async def send_personal_message(self, websocket: WebSocket, message: dict):
        try:
            await websocket.send_json(message)
        except Exception:
            pass


manager = ConnectionManager()
