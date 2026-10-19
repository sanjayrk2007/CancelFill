"""Payment orchestration: checkout, confirmation, webhooks and refunds.

Network calls to the gateway never happen while a slot/hold row lock is held:
  1. a seat is reserved with a Hold (committed),
  2. the gateway order is created,
  3. after the customer pays, the signature is verified and the hold is converted to a booking.
If payment arrives for a hold that has already ended, the money is refunded automatically.
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Booking, Hold, HoldKind, HoldStatus, Payment, PaymentStatus, Slot, SlotStatus,
)
from app.services import notification_service as notifications
from app.services import payment_ledger
from app.services.allocation_service import AlreadyHolding, accept_hold, expire_hold, sync_slot_status
from app.services.payment_gateways import BaseGateway, GatewayError, get_gateway, payment_required, to_minor_units
from app.services.state_machine import InvalidTransition, NotFoundError, OfferExpired

logger = logging.getLogger(__name__)

MAX_REFUND_ATTEMPTS = 5


class PaymentNotRequired(ValueError):
    pass


class PaymentError(Exception):
    """Signature mismatch or similar client-side payment problem."""


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _require_gateway() -> BaseGateway:
    gateway = get_gateway()
    if gateway is None:
        raise PaymentNotRequired("Payments are not enabled.")
    return gateway


def _checkout_payload(payment: Payment, hold: Hold, gateway: BaseGateway) -> Dict[str, Any]:
    return {
        "payment_id": payment.id,
        "hold_id": hold.id,
        "provider": gateway.name,
        "key_id": gateway.key_id,
        "provider_order_id": payment.provider_order_id,
        "amount": payment.amount,
        "amount_minor": to_minor_units(payment.amount),
        "currency": payment.currency,
        "expires_at": hold.expires_at,
    }


def _create_order_for_hold(db: Session, hold: Hold, slot: Slot, gateway: BaseGateway) -> Payment:
    existing = db.scalars(select(Payment).where(
        Payment.hold_id == hold.id, Payment.status == PaymentStatus.CREATED.value)).first()
    if existing:
        return existing
    amount = Decimal(slot.price)
    order_id = gateway.create_order(to_minor_units(amount), settings.PAYMENT_CURRENCY, f"hold_{hold.id[:30]}")
    payment = Payment(
        user_id=hold.user_id, slot_id=slot.id, hold_id=hold.id, amount=amount,
        currency=settings.PAYMENT_CURRENCY, provider=gateway.name, provider_order_id=order_id,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def start_checkout(
    db: Session,
    user_id: str,
    slot_id: Optional[str] = None,
    hold_id: Optional[str] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Begin paying for a free slot (slot_id) or for an accepted waitlist offer (hold_id)."""
    gateway = _require_gateway()
    current_time = now or datetime.now(timezone.utc)
    if (slot_id is None) == (hold_id is None):
        raise ValueError("Provide exactly one of slot_id or hold_id.")

    if hold_id is None:
        # Reserve a seat for the payment window. Reuse the customer's active hold if they retry.
        try:
            slot = db.scalars(select(Slot).where(Slot.id == slot_id).with_for_update()).first()
            if not slot:
                raise NotFoundError(f"Slot '{slot_id}' not found.")
            if not payment_required(slot):
                raise PaymentNotRequired("This slot does not require payment; book it directly.")
            existing = db.scalars(select(Hold).where(
                Hold.slot_id == slot.id, Hold.user_id == user_id, Hold.status == HoldStatus.ACTIVE.value)).first()
            if existing is not None:
                hold = existing
            else:
                if db.scalars(select(Booking).where(
                        Booking.slot_id == slot.id, Booking.user_id == user_id,
                        Booking.status == "CONFIRMED")).first():
                    raise AlreadyHolding("You already have a booking for this slot.")
                if slot.status != SlotStatus.AVAILABLE.value:
                    raise InvalidTransition("Slot", slot.status, SlotStatus.HELD.value)
                hold = Hold(
                    slot_id=slot.id, user_id=user_id, created_at=current_time,
                    expires_at=current_time + timedelta(seconds=settings.PAYMENT_WINDOW_SECONDS),
                    status=HoldStatus.ACTIVE.value, kind=HoldKind.CHECKOUT.value,
                )
                db.add(hold)
                db.flush()
                sync_slot_status(db, slot)
            db.commit()
            db.refresh(hold)
        except Exception:
            db.rollback()
            raise
    else:
        hold = db.get(Hold, hold_id)
        if hold is None:
            raise NotFoundError(f"Hold with id '{hold_id}' not found.")
        if hold.user_id != user_id:
            raise PermissionError("Not authorized to pay for this hold")
        slot = db.get(Slot, hold.slot_id)

    if hold.status != HoldStatus.ACTIVE.value or _aware(hold.expires_at) <= current_time:
        raise OfferExpired("This offer is no longer available")
    if not payment_required(slot):
        raise PaymentNotRequired("This slot does not require payment; accept it directly.")

    try:
        payment = _create_order_for_hold(db, hold, slot, gateway)
    except GatewayError:
        if hold.kind == HoldKind.CHECKOUT.value:
            expire_hold(db, hold.id, now=current_time)  # give the seat back
        raise
    return _checkout_payload(payment, hold, gateway)


def _finalize_paid(db: Session, payment_id: str, provider_payment_id: str, now: datetime) -> Optional[Booking]:
    """Record a captured payment and convert its hold into a booking (idempotent)."""
    payment = db.scalars(select(Payment).where(Payment.id == payment_id).with_for_update()).first()
    if payment is None:
        raise NotFoundError("Payment not found.")
    if payment.status in (PaymentStatus.PAID.value, PaymentStatus.REFUND_PENDING.value,
                          PaymentStatus.REFUNDED.value, PaymentStatus.REFUND_FAILED.value):
        booking = db.get(Booking, payment.booking_id) if payment.booking_id else None
        db.rollback()
        return booking

    late = payment.status in (PaymentStatus.EXPIRED.value, PaymentStatus.FAILED.value)
    payment.provider_payment_id = provider_payment_id
    payment.paid_at = now
    payment.status = PaymentStatus.PAID.value
    if late:
        payment_ledger.queue_refund(db, payment, "Payment captured after the hold had ended")
        db.commit()
        return None
    db.commit()

    try:
        booking = accept_hold(db, payment.hold_id, payment.user_id, now=now)
    except (OfferExpired, InvalidTransition, NotFoundError):
        payment = db.get(Payment, payment_id)
        payment_ledger.queue_refund(db, payment, "Hold ended before payment completed")
        db.commit()
        return None
    payment = db.get(Payment, payment_id)
    payment.booking_id = booking.id
    db.commit()
    db.refresh(booking)
    return booking


def confirm_payment(
    db: Session,
    payment_id: str,
    user_id: str,
    provider_order_id: str,
    provider_payment_id: str,
    signature: str,
    now: Optional[datetime] = None,
) -> Booking:
    """Called by the customer's browser after the gateway reports success."""
    gateway = _require_gateway()
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise NotFoundError("Payment not found.")
    if payment.user_id != user_id:
        raise PermissionError("Not authorized to confirm this payment")
    if provider_order_id != payment.provider_order_id or not gateway.verify_payment_signature(
        provider_order_id, provider_payment_id, signature
    ):
        raise PaymentError("Payment signature could not be verified.")
    booking = _finalize_paid(db, payment_id, provider_payment_id, now or datetime.now(timezone.utc))
    if booking is None:
        raise OfferExpired("The hold ended before payment completed. Your payment will be refunded.")
    return booking


def handle_webhook(db: Session, raw_body: bytes, signature: Optional[str], now: Optional[datetime] = None) -> str:
    """Process a verified gateway webhook. Returns a short description of what was done."""
    gateway = _require_gateway()
    if not gateway.verify_webhook(raw_body, signature):
        raise PaymentError("Invalid webhook signature.")
    current_time = now or datetime.now(timezone.utc)
    event = json.loads(raw_body)
    name = event.get("event", "")
    entity = (((event.get("payload") or {}).get("payment") or {}).get("entity")
              or ((event.get("payload") or {}).get("refund") or {}).get("entity") or {})

    if name == "payment.captured":
        payment = db.scalars(select(Payment).where(Payment.provider_order_id == entity.get("order_id"))).first()
        if payment is None:
            return "ignored: unknown order"
        _finalize_paid(db, payment.id, entity.get("id", ""), current_time)
        return "payment captured"
    if name in ("refund.processed", "refund.failed"):
        payment = db.scalars(select(Payment).where(Payment.provider_payment_id == entity.get("payment_id"))).first()
        if payment is None:
            return "ignored: unknown payment"
        if name == "refund.processed" and payment.status != PaymentStatus.REFUNDED.value:
            payment.status = PaymentStatus.REFUNDED.value
            payment.refunded_at = payment.refunded_at or current_time
            payment.refund_id = payment.refund_id or entity.get("id")
        elif name == "refund.failed" and payment.status == PaymentStatus.REFUNDED.value:
            payment.status = PaymentStatus.REFUND_FAILED.value
        db.commit()
        return name
    if name == "payment.failed":
        logger.info("payment_attempt_failed order_id=%s", entity.get("order_id"))
        return "payment failed noted"
    return f"ignored: {name or 'unknown event'}"


def process_pending_refunds(db: Session, now: Optional[datetime] = None, limit: int = 25) -> int:
    """Send queued refunds to the gateway. Returns how many succeeded."""
    gateway = get_gateway()
    if gateway is None:
        return 0
    current_time = now or datetime.now(timezone.utc)
    pending = db.scalars(
        select(Payment).where(Payment.status == PaymentStatus.REFUND_PENDING.value)
        .order_by(Payment.created_at.asc()).limit(limit).with_for_update(skip_locked=True)
    ).all()
    done = 0
    for payment in pending:
        try:
            if not payment.provider_payment_id:
                raise GatewayError("no provider payment id to refund")
            refund_id = gateway.refund(
                payment.provider_payment_id, to_minor_units(payment.amount), payment.refund_reason or "Refund"
            )
            payment.status = PaymentStatus.REFUNDED.value
            payment.refund_id = refund_id
            payment.refunded_at = current_time
            notifications.notify_refund(db, payment.user_id, f"{payment.amount:.2f}", payment.currency, now=current_time)
            done += 1
        except Exception as exc:
            payment.refund_attempts += 1
            logger.warning("refund_failed payment_id=%s attempt=%s error=%s", payment.id, payment.refund_attempts, exc)
            if payment.refund_attempts >= MAX_REFUND_ATTEMPTS:
                payment.status = PaymentStatus.REFUND_FAILED.value
        db.commit()
    return done


def simulate_mock_payment(db: Session, payment_id: str, user_id: str) -> Dict[str, str]:
    """Dev/demo only: produce the credentials a real gateway would return after the customer pays."""
    gateway = _require_gateway()
    if gateway.name != "mock":
        raise PaymentNotRequired("Simulated payments are only available with PAYMENT_PROVIDER=mock.")
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise NotFoundError("Payment not found.")
    if payment.user_id != user_id:
        raise PermissionError("Not authorized to pay this order")
    return gateway.simulate_payment(payment.provider_order_id)  # type: ignore[attr-defined]
