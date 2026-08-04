from fastapi import WebSocket
from typing import Dict, List
import json

from app.services import redis_pubsub


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str):
        await websocket.accept()
        if room not in self.active_connections:
            self.active_connections[room] = []
        self.active_connections[room].append(websocket)

    def disconnect(self, websocket: WebSocket, room: str):
        if room in self.active_connections:
            self.active_connections[room].discard(websocket) if hasattr(
                self.active_connections[room], 'discard'
            ) else None
            try:
                self.active_connections[room].remove(websocket)
            except ValueError:
                pass

    async def _local_send(self, room: str, message: dict):
        """Entrega solo a los sockets conectados a ESTE proceso."""
        if room in self.active_connections:
            dead = []
            for ws in self.active_connections[room]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(ws, room)

    async def broadcast_to_room(self, room: str, message: dict):
        # Entrega local primero, siempre: si Redis está caído o lento, los
        # clientes conectados a este mismo proceso igual reciben el evento.
        await self._local_send(room, message)
        await redis_pubsub.publish(room, message)

    async def send_personal_message(self, websocket: WebSocket, message: dict):
        try:
            await websocket.send_json(message)
        except Exception:
            pass


manager = ConnectionManager()
