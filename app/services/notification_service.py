"""Notification outbox: enqueue inside the caller's transaction, deliver afterwards.

`enqueue` only adds rows to the session; the caller's commit makes them durable together
with the state change that caused them, and a rollback discards them. `dispatch_pending`
(run by the scheduler) performs the network I/O, so no slot row lock is ever held while
talking to an email/SMS/push provider.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional, Set

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Booking,
    DeliveryStatus,
    Hold,
    Notification,
    NotificationChannel,
    NotificationDelivery,
    PushSubscription,
    Slot,
    User,
)
from app.services import notification_providers as providers

logger = logging.getLogger(__name__)

ALL_CHANNELS = {NotificationChannel.EMAIL.value, NotificationChannel.SMS.value, NotificationChannel.PUSH.value}


def _fmt(dt: datetime) -> str:
    aware = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return aware.astimezone(timezone.utc).strftime("%d %b %Y, %H:%M UTC")


def enqueue(
    db: Session,
    user_id: str,
    ntype: str,
    title: str,
    body: str,
    link: Optional[str] = None,
    show_in_app: bool = True,
    channels: Optional[Set[str]] = None,
    ignore_preferences: bool = False,
    now: Optional[datetime] = None,
) -> Optional[Notification]:
    user = db.get(User, user_id)
    if user is None:
        return None
    current_time = now or datetime.now(timezone.utc)
    wanted = channels if channels is not None else ALL_CHANNELS
    notification = Notification(
        user_id=user.id, type=ntype, title=title, body=body, link=link,
        show_in_app=show_in_app, created_at=current_time,
    )
    db.add(notification)

    def add(channel: str, destination: str) -> None:
        notification.deliveries.append(
            NotificationDelivery(channel=channel, destination=destination, next_attempt_at=current_time)
        )

    if NotificationChannel.EMAIL.value in wanted and (user.notify_email or ignore_preferences):
        add(NotificationChannel.EMAIL.value, user.email)
    if NotificationChannel.SMS.value in wanted and user.phone and (user.notify_sms or ignore_preferences):
        add(NotificationChannel.SMS.value, user.phone)
    if NotificationChannel.PUSH.value in wanted and (user.notify_push or ignore_preferences):
        for sub in db.scalars(select(PushSubscription).where(PushSubscription.user_id == user.id)).all():
            add(NotificationChannel.PUSH.value, sub.id)
    return notification


# ---- Event helpers -------------------------------------------------------------------

def notify_offer_created(db: Session, hold: Hold, slot: Slot, now: Optional[datetime] = None) -> None:
    minutes = max(1, round(settings.DEFAULT_HOLD_DURATION_SECONDS / 60))
    enqueue(
        db, hold.user_id, "OFFER_CREATED",
        "A slot you were waiting for just opened",
        f"{slot.resource_id} on {_fmt(slot.start_time)} is held for you until {_fmt(hold.expires_at)} "
        f"(about {minutes} min). Open CancelFill to accept or decline before it passes to the next person.",
        link="/offers", now=now,
    )


def notify_offer_expired(db: Session, hold: Hold, slot: Slot, now: Optional[datetime] = None) -> None:
    enqueue(
        db, hold.user_id, "OFFER_EXPIRED", "Your offer expired",
        f"The hold on {slot.resource_id} ({_fmt(slot.start_time)}) ran out and the slot moved on.",
        link="/waitlist", now=now,
    )


def notify_booking_confirmed(db: Session, booking: Booking, slot: Slot, now: Optional[datetime] = None) -> None:
    enqueue(
        db, booking.user_id, "BOOKING_CONFIRMED", "Booking confirmed",
        f"You're booked for {slot.resource_id} on {_fmt(slot.start_time)}.",
        link="/bookings", now=now,
    )


def notify_booking_cancelled(
    db: Session, booking: Booking, slot: Slot, reason: Optional[str], by_business: bool, now: Optional[datetime] = None
) -> None:
    who = "the business" if by_business else "you"
    extra = f" Reason: {reason}" if reason and by_business else ""
    enqueue(
        db, booking.user_id, "BOOKING_CANCELLED", "Booking cancelled",
        f"Your booking for {slot.resource_id} on {_fmt(slot.start_time)} was cancelled by {who}.{extra}",
        link="/bookings", now=now,
    )


def notify_refund(db: Session, user_id: str, amount: str, currency: str, now: Optional[datetime] = None) -> None:
    enqueue(
        db, user_id, "REFUND_ISSUED", "Refund issued",
        f"A refund of {currency} {amount} has been issued to your original payment method.",
        link="/bookings", now=now,
    )


def notify_password_reset(db: Session, user_id: str, reset_link: str, now: Optional[datetime] = None) -> None:
    minutes = settings.PASSWORD_RESET_EXPIRE_MINUTES
    enqueue(
        db, user_id, "PASSWORD_RESET", "Reset your CancelFill password",
        f"Use this link to choose a new password (valid for {minutes} minutes): {reset_link}\n\n"
        "If you didn't ask for this, you can ignore this email.",
        show_in_app=False, channels={NotificationChannel.EMAIL.value}, ignore_preferences=True, now=now,
    )


# ---- Dispatch ------------------------------------------------------------------------

def _deliver(db: Session, delivery: NotificationDelivery) -> None:
    n = delivery.notification
    if delivery.channel == NotificationChannel.EMAIL.value:
        providers.senders["EMAIL"](delivery.destination, n.title, n.body)
    elif delivery.channel == NotificationChannel.SMS.value:
        providers.senders["SMS"](delivery.destination, f"{n.title}: {n.body}")
    elif delivery.channel == NotificationChannel.PUSH.value:
        sub = db.get(PushSubscription, delivery.destination)
        if sub is None:
            raise providers.PermanentDeliveryError("push subscription no longer exists")
        info = {"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}}
        try:
            providers.senders["PUSH"](info, n.title, n.body, n.link)
        except providers.PermanentDeliveryError:
            db.delete(sub)
            raise


def dispatch_pending(db: Session, now: Optional[datetime] = None, limit: int = 50) -> int:
    """Send due deliveries one at a time, committing after each. Returns how many were sent."""
    current_time = now or datetime.now(timezone.utc)
    due = db.scalars(
        select(NotificationDelivery)
        .where(
            NotificationDelivery.status == DeliveryStatus.PENDING.value,
            NotificationDelivery.next_attempt_at <= current_time,
        )
        .order_by(NotificationDelivery.next_attempt_at.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
    ).all()
    sent = 0
    for delivery in due:
        try:
            _deliver(db, delivery)
            delivery.status = DeliveryStatus.SENT.value
            delivery.sent_at = current_time
            delivery.last_error = None
            sent += 1
        except providers.PermanentDeliveryError as exc:
            delivery.status = DeliveryStatus.FAILED.value
            delivery.last_error = str(exc)[:500]
        except Exception as exc:  # network/provider hiccup: retry with backoff
            delivery.attempts += 1
            delivery.last_error = str(exc)[:500]
            if delivery.attempts >= settings.NOTIFICATION_MAX_ATTEMPTS:
                delivery.status = DeliveryStatus.FAILED.value
            else:
                delivery.next_attempt_at = current_time + timedelta(seconds=min(30 * 2 ** delivery.attempts, 1800))
            logger.warning("notification_delivery_failed id=%s channel=%s error=%s", delivery.id, delivery.channel, exc)
        db.commit()
    return sent
