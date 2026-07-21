import json
from typing import Optional
from sqlalchemy.orm import Session
from app.modules.visits.entities import PushSubscription
from app.core.config import settings


def send_push_notification(subscription: PushSubscription, title: str, body: str, data: dict = None) -> bool:
    if not settings.VAPID_PRIVATE_KEY:
        return False
    try:
        from pywebpush import webpush, WebPushException
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=json.dumps({"title": title, "body": body, "data": data or {}}),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": settings.VAPID_EMAIL},
        )
        return True
    except Exception:
        return False


def notify_photo_rejected(db: Session, mercaderista_cedula: str, foto_id: int, motivo: str) -> None:
    subs = db.query(PushSubscription).filter(
        PushSubscription.mercaderista_cedula == mercaderista_cedula
    ).all()
    for sub in subs:
        send_push_notification(
            sub,
            title="Foto rechazada",
            body=f"Una de tus fotos fue rechazada: {motivo}",
            data={"foto_id": foto_id, "type": "foto_rechazada"},
        )
