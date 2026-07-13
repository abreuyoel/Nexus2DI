from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.models.foto import PushSubscription
from app.core.config import settings

router = APIRouter(prefix="/api/push", tags=["Push Notifications"])


class SubscriptionCreate(BaseModel):
    endpoint: str
    p256dh: str
    auth: str
    mercaderista_cedula: str | None = None


@router.get("/vapid-public-key")
def get_vapid_key():
    return {"public_key": settings.VAPID_PUBLIC_KEY}


@router.post("/subscribe")
def subscribe(
    data: SubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    existing = db.query(PushSubscription).filter(
        PushSubscription.endpoint == data.endpoint
    ).first()
    if existing:
        existing.p256dh = data.p256dh
        existing.auth = data.auth
        db.commit()
        return {"message": "Suscripción actualizada"}

    sub = PushSubscription(
        user_id=current_user.id,
        endpoint=data.endpoint,
        p256dh=data.p256dh,
        auth=data.auth,
        mercaderista_cedula=data.mercaderista_cedula,
    )
    db.add(sub)
    db.commit()
    return {"message": "Suscripción creada exitosamente"}


@router.delete("/unsubscribe")
def unsubscribe(
    endpoint: str,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    db.query(PushSubscription).filter(PushSubscription.endpoint == endpoint).delete()
    db.commit()
    return {"message": "Suscripción eliminada"}
