import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.config import settings
from app.models import (
    Slot,
    SlotStatus,
    WaitlistEntry,
    WaitlistStatus,
    Hold,
    HoldStatus,
    Booking,
    BookingStatus,
    BookingSource,
    User,
)

logger = logging.getLogger(__name__)
from app.services.state_machine import (
    assert_transition,
    InvalidTransition,
    OfferExpired,
    NotFoundError,
    ReasonRequired,
)

def _offer_next_candidate(
    db: Session,
    slot: Slot,
    current_time: datetime
) -> Tuple[Optional[Hold], Optional[WaitlistEntry]]:
    if slot.status != SlotStatus.AVAILABLE.value:
        return None, None
    entry = db.scalars(
        select(WaitlistEntry)
        .where(
            WaitlistEntry.slot_id == slot.id,
            WaitlistEntry.status == WaitlistStatus.WAITING.value
        )
        .order_by(WaitlistEntry.joined_at.asc(), WaitlistEntry.id.asc())
    ).first()
    if not entry:
        return None, None
    assert_transition("WaitlistEntry", entry.status, WaitlistStatus.OFFERED.value)
    entry.status = WaitlistStatus.OFFERED.value
    assert_transition("Slot", slot.status, SlotStatus.HELD.value)
    slot.status = SlotStatus.HELD.value
    expires_at = current_time + timedelta(seconds=settings.DEFAULT_HOLD_DURATION_SECONDS)
    hold = Hold(
        slot_id=slot.id,
        user_id=entry.user_id,
        created_at=current_time,
        expires_at=expires_at,
        status=HoldStatus.ACTIVE.value
    )
    db.add(hold)
    db.flush()
    logger.info("offer_created hold_id=%s slot_id=%s user_id=%s", hold.id, hold.slot_id, hold.user_id)
    return hold, entry

def book_slot(
    db: Session,
    slot_id: str,
    user_id: str,
    now: Optional[datetime] = None
) -> Booking:
    try:
        slot = db.scalars(select(Slot).where(Slot.id == slot_id).with_for_update()).first()
        if not slot:
            raise NotFoundError(f"Slot '{slot_id}' not found.")
        if slot.status != SlotStatus.AVAILABLE.value:
            raise InvalidTransition("Slot", slot.status, SlotStatus.BOOKED.value)
        assert_transition("Slot", slot.status, SlotStatus.BOOKED.value)
        current_time = now or datetime.now(timezone.utc)
        booking = Booking(
            slot_id=slot.id,
            user_id=user_id,
            booked_at=current_time,
            status=BookingStatus.CONFIRMED.value,
            source=BookingSource.DIRECT.value,
            recovered_from_booking_id=None
        )
        slot.status = SlotStatus.BOOKED.value
        db.add(booking)
        db.commit()
        db.refresh(booking)
        return booking
    except Exception:
        db.rollback()
        raise

def cancel_booking(
    db: Session,
    booking_id: str,
    actor: User | str,
    now: Optional[datetime] = None,
    reason: Optional[str] = None
) -> Dict[str, Any]:
    try:
        booking = db.scalars(select(Booking).where(Booking.id == booking_id).with_for_update()).first()
        if not booking:
            raise NotFoundError(f"Booking with id '{booking_id}' not found.")
        slot = db.scalars(select(Slot).where(Slot.id == booking.slot_id).with_for_update()).first()
        if not slot:
            raise NotFoundError(f"Associated slot '{booking.slot_id}' not found.")
        actor_id = actor.id if isinstance(actor, User) else str(actor)
        if booking.user_id != actor_id and slot.owner_id != actor_id:
            raise PermissionError("Not authorized to cancel this booking")
        if slot.owner_id == actor_id and not reason:
            raise ReasonRequired("A cancellation reason is required for business cancellations")
        assert_transition("Booking", booking.status, BookingStatus.CANCELLED.value)
        booking.status = BookingStatus.CANCELLED.value
        booking.cancellation_reason = reason
        booking.cancelled_by_role = "BUSINESS" if slot.owner_id == actor_id else "CUSTOMER"
        assert_transition("Slot", slot.status, SlotStatus.AVAILABLE.value)
        slot.status = SlotStatus.AVAILABLE.value
        current_time = now or datetime.now(timezone.utc)
        hold, earliest_candidate = _offer_next_candidate(db, slot, current_time)
        db.commit()
        db.refresh(booking)
        if hold:
            db.refresh(hold)
        return {
            "booking_id": booking.id,
            "booking_status": booking.status,
            "slot_id": slot.id,
            "slot_status": slot.status,
            "candidate_selected": hold is not None,
            "selected_user_id": earliest_candidate.user_id if earliest_candidate else None,
            "hold": hold,
            "message": (
                f"Booking cancelled. Slot recovered and offered to earliest candidate '{earliest_candidate.user_id}' with temporary hold."
                if earliest_candidate
                else "Booking cancelled. No waitlist candidates found; slot is now AVAILABLE."
            )
        }
    except Exception:
        db.rollback()
        raise

def offer_next_candidate(
    db: Session,
    slot_id: str,
    now: Optional[datetime] = None
) -> Optional[Hold]:
    try:
        slot = db.scalars(select(Slot).where(Slot.id == slot_id).with_for_update()).first()
        if not slot:
            raise NotFoundError(f"Slot '{slot_id}' not found.")
        current_time = now or datetime.now(timezone.utc)
        hold, _ = _offer_next_candidate(db, slot, current_time)
        db.commit()
        if hold:
            db.refresh(hold)
        return hold
    except Exception:
        db.rollback()
        raise

def accept_hold(
    db: Session,
    hold_id: str,
    user_id: str,
    now: Optional[datetime] = None
) -> Booking:
    try:
        hold = db.scalars(select(Hold).where(Hold.id == hold_id).with_for_update()).first()
        if not hold:
            raise NotFoundError(f"Hold with id '{hold_id}' not found.")
        slot = db.scalars(select(Slot).where(Slot.id == hold.slot_id).with_for_update()).first()
        if not slot:
            raise NotFoundError(f"Associated slot '{hold.slot_id}' not found.")
        if hold.user_id != user_id:
            raise PermissionError("Not authorized to accept this hold")
        current_time = now or datetime.now(timezone.utc)
        expires_at = hold.expires_at if hold.expires_at.tzinfo else hold.expires_at.replace(tzinfo=timezone.utc)
        if current_time > expires_at:
            assert_transition("Hold", hold.status, HoldStatus.EXPIRED.value)
            hold.status = HoldStatus.EXPIRED.value
            logger.info("hold_expired hold_id=%s slot_id=%s user_id=%s", hold.id, hold.slot_id, hold.user_id)
            entry = db.scalars(
                select(WaitlistEntry).where(
                    WaitlistEntry.slot_id == slot.id,
                    WaitlistEntry.user_id == hold.user_id,
                    WaitlistEntry.status == WaitlistStatus.OFFERED.value
                )
            ).first()
            if entry:
                assert_transition("WaitlistEntry", entry.status, WaitlistStatus.EXPIRED.value)
                entry.status = WaitlistStatus.EXPIRED.value
            assert_transition("Slot", slot.status, SlotStatus.AVAILABLE.value)
            slot.status = SlotStatus.AVAILABLE.value
            _offer_next_candidate(db, slot, current_time)
            db.commit()
            raise OfferExpired("This offer is no longer available")
        assert_transition("Hold", hold.status, HoldStatus.CONFIRMED.value)
        hold.status = HoldStatus.CONFIRMED.value
        entry = db.scalars(
            select(WaitlistEntry).where(
                WaitlistEntry.slot_id == slot.id,
                WaitlistEntry.user_id == hold.user_id,
                WaitlistEntry.status == WaitlistStatus.OFFERED.value
            )
        ).first()
        if entry:
            assert_transition("WaitlistEntry", entry.status, WaitlistStatus.CONFIRMED.value)
            entry.status = WaitlistStatus.CONFIRMED.value
        assert_transition("Slot", slot.status, SlotStatus.BOOKED.value)
        slot.status = SlotStatus.BOOKED.value
        prev_booking = db.scalars(
            select(Booking)
            .where(
                Booking.slot_id == slot.id,
                Booking.status == BookingStatus.CANCELLED.value
            )
            .order_by(Booking.booked_at.desc())
        ).first()
        booking = Booking(
            slot_id=slot.id,
            user_id=user_id,
            booked_at=current_time,
            status=BookingStatus.CONFIRMED.value,
            source=BookingSource.RECOVERED.value,
            recovered_from_booking_id=prev_booking.id if prev_booking else None
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        return booking
    except OfferExpired:
        raise
    except Exception:
        db.rollback()
        raise

def decline_hold(
    db: Session,
    hold_id: str,
    user_id: str,
    now: Optional[datetime] = None
) -> Hold:
    try:
        hold = db.scalars(select(Hold).where(Hold.id == hold_id).with_for_update()).first()
        if not hold:
            raise NotFoundError(f"Hold with id '{hold_id}' not found.")
        slot = db.scalars(select(Slot).where(Slot.id == hold.slot_id).with_for_update()).first()
        if not slot:
            raise NotFoundError(f"Associated slot '{hold.slot_id}' not found.")
        if hold.user_id != user_id:
            raise PermissionError("Not authorized to decline this hold")
        assert_transition("Hold", hold.status, HoldStatus.DECLINED.value)
        hold.status = HoldStatus.DECLINED.value
        entry = db.scalars(
            select(WaitlistEntry).where(
                WaitlistEntry.slot_id == slot.id,
                WaitlistEntry.user_id == hold.user_id,
                WaitlistEntry.status == WaitlistStatus.OFFERED.value
            )
        ).first()
        if entry:
            assert_transition("WaitlistEntry", entry.status, WaitlistStatus.DECLINED.value)
            entry.status = WaitlistStatus.DECLINED.value
        assert_transition("Slot", slot.status, SlotStatus.AVAILABLE.value)
        slot.status = SlotStatus.AVAILABLE.value
        current_time = now or datetime.now(timezone.utc)
        _offer_next_candidate(db, slot, current_time)
        db.commit()
        db.refresh(hold)
        return hold
    except Exception:
        db.rollback()
        raise

def expire_hold(
    db: Session,
    hold_id: str,
    now: Optional[datetime] = None
) -> Hold:
    try:
        hold = db.scalars(select(Hold).where(Hold.id == hold_id).with_for_update()).first()
        if not hold:
            raise NotFoundError(f"Hold with id '{hold_id}' not found.")
        slot = db.scalars(select(Slot).where(Slot.id == hold.slot_id).with_for_update()).first()
        if not slot:
            raise NotFoundError(f"Associated slot '{hold.slot_id}' not found.")
        assert_transition("Hold", hold.status, HoldStatus.EXPIRED.value)
        hold.status = HoldStatus.EXPIRED.value
        logger.info("hold_expired hold_id=%s slot_id=%s user_id=%s", hold.id, hold.slot_id, hold.user_id)
        entry = db.scalars(
            select(WaitlistEntry).where(
                WaitlistEntry.slot_id == slot.id,
                WaitlistEntry.user_id == hold.user_id,
                WaitlistEntry.status == WaitlistStatus.OFFERED.value
            )
        ).first()
        if entry:
            assert_transition("WaitlistEntry", entry.status, WaitlistStatus.EXPIRED.value)
            entry.status = WaitlistStatus.EXPIRED.value
        assert_transition("Slot", slot.status, SlotStatus.AVAILABLE.value)
        slot.status = SlotStatus.AVAILABLE.value
        current_time = now or datetime.now(timezone.utc)
        _offer_next_candidate(db, slot, current_time)
        db.commit()
        db.refresh(hold)
        return hold
    except Exception:
        db.rollback()
        raise

def join_waitlist(
    db: Session,
    slot_id: str,
    user_id: str,
    joined_at: Optional[datetime] = None,
    now: Optional[datetime] = None
) -> WaitlistEntry:
    try:
        slot = db.scalars(select(Slot).where(Slot.id == slot_id).with_for_update()).first()
        if not slot:
            raise NotFoundError(f"Slot '{slot_id}' not found.")
        if slot.status not in (SlotStatus.BOOKED.value, SlotStatus.HELD.value):
            raise ValueError(f"Cannot join waitlist for slot '{slot_id}': status is '{slot.status}', must be BOOKED or HELD.")
        active_booking = db.scalars(
            select(Booking).where(
                Booking.slot_id == slot.id,
                Booking.status == BookingStatus.CONFIRMED.value,
                Booking.user_id == user_id
            )
        ).first()
        if active_booking:
            raise ValueError("Current booking holder cannot join the waitlist.")
        active_hold = db.scalars(
            select(Hold).where(
                Hold.slot_id == slot.id,
                Hold.status == HoldStatus.ACTIVE.value,
                Hold.user_id == user_id
            )
        ).first()
        if active_hold:
            raise ValueError("Current hold holder cannot join the waitlist.")
        existing_entry = db.scalars(
            select(WaitlistEntry).where(
                WaitlistEntry.slot_id == slot.id,
                WaitlistEntry.user_id == user_id,
                WaitlistEntry.status.in_([WaitlistStatus.WAITING.value, WaitlistStatus.OFFERED.value])
            )
        ).first()
        if existing_entry:
            raise ValueError("User already has an active waitlist entry for this slot.")
        current_time = joined_at or now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
        entry = WaitlistEntry(
            slot_id=slot.id,
            user_id=user_id,
            joined_at=current_time,
            status=WaitlistStatus.WAITING.value
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    except Exception:
        db.rollback()
        raise

def leave_waitlist(
    db: Session,
    waitlist_id: str,
    actor: User | str,
    now: Optional[datetime] = None
) -> WaitlistEntry:
    try:
        entry = db.scalars(select(WaitlistEntry).where(WaitlistEntry.id == waitlist_id)).first()
        if not entry:
            raise NotFoundError(f"Waitlist entry '{waitlist_id}' not found.")
        slot = db.scalars(select(Slot).where(Slot.id == entry.slot_id).with_for_update()).first()
        if not slot:
            raise NotFoundError(f"Associated slot '{entry.slot_id}' not found.")
        actor_id = actor.id if isinstance(actor, User) else str(actor)
        if entry.user_id != actor_id:
            raise PermissionError("Not authorized to remove this waitlist entry")
        assert_transition("WaitlistEntry", entry.status, WaitlistStatus.CANCELLED.value)
        entry.status = WaitlistStatus.CANCELLED.value
        db.commit()
        db.refresh(entry)
        return entry
    except Exception:
        db.rollback()
        raise

def get_waitlist_for_slot(db: Session, slot_id: str) -> list[WaitlistEntry]:
    return list(
        db.scalars(
            select(WaitlistEntry)
            .where(
                WaitlistEntry.slot_id == slot_id,
                WaitlistEntry.status == WaitlistStatus.WAITING.value
            )
            .order_by(WaitlistEntry.joined_at.asc(), WaitlistEntry.id.asc())
        ).all()
    )


def cancel_past_slot(
    db: Session,
    slot_id: str,
    now: Optional[datetime] = None
) -> bool:
    """Cancel an unbooked slot whose start time has passed.

    Only AVAILABLE or HELD slots are cancelled. BOOKED slots are completed
    appointments and are left untouched. Returns True if the slot was cancelled.
    """
    try:
        slot = db.scalars(select(Slot).where(Slot.id == slot_id).with_for_update()).first()
        if not slot:
            raise NotFoundError(f"Slot '{slot_id}' not found.")
        current_time = now or datetime.now(timezone.utc)
        start = slot.start_time if slot.start_time.tzinfo else slot.start_time.replace(tzinfo=timezone.utc)
        if start > current_time or slot.status not in (SlotStatus.AVAILABLE.value, SlotStatus.HELD.value):
            db.rollback()
            return False
        for hold in db.scalars(
            select(Hold).where(Hold.slot_id == slot.id, Hold.status == HoldStatus.ACTIVE.value)
        ).all():
            assert_transition("Hold", hold.status, HoldStatus.EXPIRED.value)
            hold.status = HoldStatus.EXPIRED.value
        for entry in db.scalars(
            select(WaitlistEntry).where(
                WaitlistEntry.slot_id == slot.id,
                WaitlistEntry.status.in_([WaitlistStatus.WAITING.value, WaitlistStatus.OFFERED.value]),
            )
        ).all():
            target = (
                WaitlistStatus.CANCELLED.value
                if entry.status == WaitlistStatus.WAITING.value
                else WaitlistStatus.EXPIRED.value
            )
            assert_transition("WaitlistEntry", entry.status, target)
            entry.status = target
        assert_transition("Slot", slot.status, SlotStatus.CANCELLED.value)
        slot.status = SlotStatus.CANCELLED.value
        logger.info("past_slot_cancelled slot_id=%s", slot.id)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
