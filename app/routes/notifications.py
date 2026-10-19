from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Notification, PushSubscription, User
from app.schemas import (
    NotificationListResponse, NotificationResponse, PushConfigResponse, PushSubscribeRequest, PushUnsubscribeRequest,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationListResponse, summary="My in-app notifications")
def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationListResponse:
    base = (Notification.user_id == current_user.id, Notification.show_in_app.is_(True))
    query = select(Notification).where(*base)
    if unread_only:
        query = query.where(Notification.read_at.is_(None))
    items = db.scalars(query.order_by(Notification.created_at.desc(), Notification.id.asc()).limit(limit)).all()
    unread = db.scalar(select(func.count(Notification.id)).where(*base, Notification.read_at.is_(None))) or 0
    return NotificationListResponse(
        unread_count=int(unread), items=[NotificationResponse.model_validate(n) for n in items]
    )


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT, summary="Mark all my notifications read")
def mark_all_read(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Response:
    db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.read_at.is_(None))
        .values(read_at=datetime.now(timezone.utc))
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{notification_id}/read", response_model=NotificationResponse, summary="Mark one notification read")
def mark_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Notification:
    n = db.get(Notification, notification_id)
    if n is None or n.user_id != current_user.id or not n.show_in_app:
        raise HTTPException(status_code=404, detail="Notification not found")
    if n.read_at is None:
        n.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(n)
    return n


@router.get("/push/config", response_model=PushConfigResponse, summary="Web Push public key")
def push_config() -> PushConfigResponse:
    enabled = bool(settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY)
    return PushConfigResponse(enabled=enabled, public_key=settings.VAPID_PUBLIC_KEY or None)


@router.post("/push/subscribe", status_code=status.HTTP_204_NO_CONTENT, summary="Register this browser for push")
def push_subscribe(
    body: PushSubscribeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    existing = db.scalars(select(PushSubscription).where(PushSubscription.endpoint == body.endpoint)).first()
    if existing:
        existing.user_id = current_user.id  # same browser, new account
        existing.p256dh, existing.auth = body.keys.p256dh, body.keys.auth
    else:
        db.add(PushSubscription(
            user_id=current_user.id, endpoint=body.endpoint, p256dh=body.keys.p256dh, auth=body.keys.auth))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/push/unsubscribe", status_code=status.HTTP_204_NO_CONTENT, summary="Remove this browser from push")
def push_unsubscribe(
    body: PushUnsubscribeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    sub: Optional[PushSubscription] = db.scalars(select(PushSubscription).where(
        PushSubscription.endpoint == body.endpoint, PushSubscription.user_id == current_user.id)).first()
    if sub:
        db.delete(sub)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
