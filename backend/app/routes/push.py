from sqlalchemy import select, delete as sa_delete
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.db.session import get_async_db
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
async def get_vapid_key():
    return {"public_key": settings.VAPID_PUBLIC_KEY}


@router.post("/subscribe")
async def subscribe(
    data: SubscriptionCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(get_current_user),
):
    existing = (await db.execute(
        select(PushSubscription).filter(PushSubscription.endpoint == data.endpoint)
    )).scalars().first()
    if existing:
        existing.p256dh = data.p256dh
        existing.auth = data.auth
        await db.commit()
        return {"message": "Suscripción actualizada"}

    sub = PushSubscription(
        user_id=current_user.id,
        endpoint=data.endpoint,
        p256dh=data.p256dh,
        auth=data.auth,
        mercaderista_cedula=data.mercaderista_cedula,
    )
    db.add(sub)
    await db.commit()
    return {"message": "Suscripción creada exitosamente"}


@router.delete("/unsubscribe")
async def unsubscribe(
    endpoint: str,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    await db.execute(sa_delete(PushSubscription).where(PushSubscription.endpoint == endpoint))
    await db.commit()
    return {"message": "Suscripción eliminada"}
