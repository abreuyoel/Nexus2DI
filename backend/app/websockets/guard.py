import time
import logging
from typing import Dict, Optional
from fastapi import WebSocket, status
from app.core.config import settings
from app.core.security import decode_token
from app.db.session import SessionLocal
from app.modules.auth.entities import Usuario

logger = logging.getLogger("app.websockets")


class TokenBucket:
    """Token Bucket rate limiter algorithm for WebSocket connections.

    Tokens refill continuously over time up to a maximum capacity.
    """

    def __init__(self, capacity: float = 20.0, refill_rate: float = 5.0):
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)  # tokens per second
        self.tokens = float(capacity)
        self.last_update = time.monotonic()

    def consume(self, amount: float = 1.0) -> bool:
        now = time.monotonic()
        delta = now - self.last_update
        self.last_update = now
        # Refill tokens according to time delta
        self.tokens = min(self.capacity, self.tokens + delta * self.refill_rate)

        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False


def get_allowed_origins() -> set[str]:
    return {o.rstrip("/") for o in settings.ALLOWED_ORIGINS}


class WebSocketGuard:
    """Guard for WebSockets: CORS check, Token-based Auth & Token Bucket Rate Limiter."""

    def __init__(self, capacity: float = 20.0, refill_rate: float = 5.0):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.limiters: Dict[WebSocket, TokenBucket] = {}

    def check_cors(self, websocket: WebSocket) -> bool:
        """Validate Origin header against CORS whitelist."""
        origin = websocket.headers.get("origin")
        if not origin:
            return True
        origin_clean = origin.rstrip("/")
        allowed = get_allowed_origins()
        return any(origin_clean.startswith(a) for a in allowed)

    def authenticate(self, websocket: WebSocket) -> Optional[Usuario]:
        """Authenticate user via token query param, Authorization header or Sec-WebSocket-Protocol."""
        token = websocket.query_params.get("token")
        if not token:
            auth_header = websocket.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
        if not token:
            subprotocol = websocket.headers.get("sec-websocket-protocol")
            if subprotocol:
                token = subprotocol.split(",")[0].strip()

        if not token:
            return None

        try:
            payload = decode_token(token)
            user_id = payload.get("sub")
            if not user_id:
                return None

            db = SessionLocal()
            try:
                user = db.query(Usuario).filter(Usuario.id == int(user_id), Usuario.activo == True).first()
                return user
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"WebSocket auth error: {e}")
            return None

    def check_rate_limit(self, websocket: WebSocket, amount: float = 1.0) -> bool:
        """Consume tokens from the token bucket for this connection."""
        if websocket not in self.limiters:
            self.limiters[websocket] = TokenBucket(self.capacity, self.refill_rate)
        return self.limiters[websocket].consume(amount)

    def remove_limiter(self, websocket: WebSocket) -> None:
        self.limiters.pop(websocket, None)


ws_guard = WebSocketGuard(capacity=20.0, refill_rate=5.0)
