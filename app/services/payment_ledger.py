"""Database-only payment bookkeeping used inside allocation transactions.

Nothing here performs network I/O. Refunds are only *queued* (status REFUND_PENDING); the
payment service sends them to the gateway after the transaction has committed.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Booking, Payment, PaymentStatus, Slot

logger = logging.getLogger(__name__)


def close_payments_for_hold(db: Session, hold_id: str) -> None:
    """A hold ended without a booking: any still-unpaid order for it can no longer be used."""
    for payment in db.scalars(select(Payment).where(Payment.hold_id == hold_id)).all():
        if payment.status == PaymentStatus.CREATED.value:
            payment.status = PaymentStatus.EXPIRED.value
        elif payment.status == PaymentStatus.PAID.value and payment.booking_id is None:
            # Money was taken but the seat is gone: give it back.
            queue_refund(db, payment, "Hold ended before booking was confirmed")


def queue_refund(db: Session, payment: Payment, reason: str) -> None:
    if payment.status == PaymentStatus.PAID.value:
        payment.status = PaymentStatus.REFUND_PENDING.value
        payment.refund_reason = reason
        logger.info("refund_queued payment_id=%s reason=%s", payment.id, reason)


def refund_for_cancelled_booking(
    db: Session, booking: Booking, slot: Slot, by_business: bool, now: Optional[datetime] = None
) -> Optional[Payment]:
    """Queue a refund for a cancelled booking according to the cancellation policy.

    Business-initiated cancellations (and slot removals) are always refunded in full.
    Customer cancellations are refunded only if made at least REFUND_CUTOFF_HOURS before start.
    """
    payment = db.scalars(
        select(Payment).where(Payment.booking_id == booking.id, Payment.status == PaymentStatus.PAID.value)
    ).first()
    if payment is None:
        return None
    current_time = now or datetime.now(timezone.utc)
    start = slot.start_time if slot.start_time.tzinfo else slot.start_time.replace(tzinfo=timezone.utc)
    within_window = start - current_time >= timedelta(hours=settings.REFUND_CUTOFF_HOURS)
    if by_business:
        queue_refund(db, payment, "Cancelled by business")
    elif within_window:
        queue_refund(db, payment, "Cancelled by customer within refund window")
    else:
        logger.info("refund_denied payment_id=%s reason=outside_refund_window", payment.id)
        return None
    return payment
