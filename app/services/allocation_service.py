import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.config import settings
from app.models import (
    HoldKind,
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
    UserRole,
)

logger = logging.getLogger(__name__)
from app.services import notification_service as notifications
from app.services import payment_ledger
from app.services.state_machine import (
    assert_transition,
    InvalidTransition,
    OfferExpired,
    NotFoundError,
    ReasonRequired,
)

# A slot is one bookable unit (SRS 1.4, NFR-03): it can never confirm for more than one customer.
# `Slot.capacity` is descriptive and deliberately plays no part in allocation.
SEATS_PER_SLOT = 1


class AlreadyHolding(ValueError):
    """The customer already has a confirmed booking or an active hold on this slot."""


class EligibilityResult:
    def __init__(self, eligible: bool, reason: Optional[str] = None):
        self.eligible = eligible
        self.reason = reason

    def __bool__(self) -> bool:
        return self.eligible

    def __iter__(self):
        return iter((self.eligible, self.reason))

    def __getitem__(self, index):
        return (self.eligible, self.reason)[index]

    def __eq__(self, other):
        if isinstance(other, bool):
            return self.eligible == other
        if isinstance(other, tuple):
            return (self.eligible, self.reason) == other
        return super().__eq__(other)


def is_candidate_eligible(
    db: Session,
    entry: WaitlistEntry,
    slot: Slot
) -> EligibilityResult:
    if entry.status != WaitlistStatus.WAITING.value:
        return EligibilityResult(False, f"waitlist entry status is {entry.status}, expected WAITING")
    user = db.get(User, entry.user_id)
    if not user:
        return EligibilityResult(False, "user does not exist")
    if not user.is_active:
        return EligibilityResult(False, "user is inactive")
    if user.role != UserRole.CUSTOMER.value:
        return EligibilityResult(False, f"user role is {user.role}, expected CUSTOMER")
    has_booking = db.scalar(
        select(func.count(Booking.id)).where(
            Booking.slot_id == slot.id,
            Booking.user_id == entry.user_id,
            Booking.status == BookingStatus.CONFIRMED.value,
        )
    ) or 0
    if has_booking > 0:
        return EligibilityResult(False, "user already has a confirmed booking for this slot")
    has_hold = db.scalar(
        select(func.count(Hold.id)).where(
            Hold.slot_id == slot.id,
            Hold.user_id == entry.user_id,
            Hold.status == HoldStatus.ACTIVE.value,
        )
    ) or 0
    if has_hold > 0:
        return EligibilityResult(False, "user already has an active hold for this slot")
    return EligibilityResult(True, None)


is_eligible_candidate = is_candidate_eligible
check_candidate_eligibility = is_candidate_eligible


def _seat_counts(db: Session, slot: Slot) -> Tuple[int, int]:
    """(confirmed bookings, active holds) for a slot. Callers must hold the slot row lock."""
    db.flush()
    confirmed = db.scalar(
        select(func.count(Booking.id)).where(
            Booking.slot_id == slot.id, Booking.status == BookingStatus.CONFIRMED.value
        )
    ) or 0
    holds = db.scalar(
        select(func.count(Hold.id)).where(Hold.slot_id == slot.id, Hold.status == HoldStatus.ACTIVE.value)
    ) or 0
    return int(confirmed), int(holds)


def free_seats(db: Session, slot: Slot) -> int:
    confirmed, holds = _seat_counts(db, slot)
    return SEATS_PER_SLOT - confirmed - holds


def _set_slot_status(slot: Slot, target: str) -> None:
    current = slot.status
    if current == target:
        return
    try:
        assert_transition("Slot", current, target)
    except InvalidTransition:
        # e.g. BOOKED -> HELD: a seat is freed and immediately re-held, so pass through AVAILABLE.
        assert_transition("Slot", current, SlotStatus.AVAILABLE.value)
        assert_transition("Slot", SlotStatus.AVAILABLE.value, target)
    slot.status = target


def sync_slot_status(db: Session, slot: Slot) -> None:
    """Derive slot status from seat usage: free seat -> AVAILABLE, full with holds -> HELD, full -> BOOKED."""
    if slot.status == SlotStatus.CANCELLED.value:
        return
    confirmed, holds = _seat_counts(db, slot)
    if SEATS_PER_SLOT - confirmed - holds > 0:
        target = SlotStatus.AVAILABLE.value
    elif holds > 0:
        target = SlotStatus.HELD.value
    else:
        target = SlotStatus.BOOKED.value
    _set_slot_status(slot, target)


def _offer_next_candidate(
    db: Session,
    slot: Slot,
    current_time: datetime
) -> Tuple[Optional[Hold], Optional[WaitlistEntry]]:
    if slot.status == SlotStatus.CANCELLED.value or free_seats(db, slot) <= 0:
        return None, None
    entries = db.scalars(
        select(WaitlistEntry)
        .where(
            WaitlistEntry.slot_id == slot.id,
            WaitlistEntry.status == WaitlistStatus.WAITING.value
        )
        .order_by(WaitlistEntry.joined_at.asc(), WaitlistEntry.id.asc())
    ).all()
    for entry in entries:
        eligible, reason = is_candidate_eligible(db, entry, slot)
        if not eligible:
            assert_transition("WaitlistEntry", entry.status, WaitlistStatus.CANCELLED.value)
            entry.status = WaitlistStatus.CANCELLED.value
            db.flush()
            logger.info(
                "waitlist_candidate_ineligible entry_id=%s slot_id=%s user_id=%s reason=%s",
                entry.id,
                slot.id,
                entry.user_id,
                reason,
            )
            continue
        assert_transition("WaitlistEntry", entry.status, WaitlistStatus.OFFERED.value)
        entry.status = WaitlistStatus.OFFERED.value
        expires_at = current_time + timedelta(seconds=settings.DEFAULT_HOLD_DURATION_SECONDS)
        hold = Hold(
            slot_id=slot.id,
            user_id=entry.user_id,
            created_at=current_time,
            expires_at=expires_at,
            status=HoldStatus.ACTIVE.value,
            kind=HoldKind.OFFER.value,
        )
        db.add(hold)
        db.flush()
        sync_slot_status(db, slot)
        notifications.notify_offer_created(db, hold, slot, now=current_time)
        logger.info("offer_created hold_id=%s slot_id=%s user_id=%s", hold.id, hold.slot_id, hold.user_id)
        return hold, entry
    sync_slot_status(db, slot)
    return None, None


def offer_all_candidates(
    db: Session,
    slot: Slot,
    current_time: datetime
) -> Tuple[Optional[Hold], Optional[WaitlistEntry]]:
    """Offer the freed slot to the next waiting customer. Returns the offer made, if any."""
    first: Tuple[Optional[Hold], Optional[WaitlistEntry]] = (None, None)
    while True:
        hold, entry = _offer_next_candidate(db, slot, current_time)
        if hold is None:
            return first
        if first[0] is None:
            first = (hold, entry)

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
        existing_booking = db.scalars(
            select(Booking).where(
                Booking.slot_id == slot.id,
                Booking.user_id == user_id,
                Booking.status == BookingStatus.CONFIRMED.value,
            )
        ).first()
        existing_hold = db.scalars(
            select(Hold).where(
                Hold.slot_id == slot.id,
                Hold.user_id == user_id,
                Hold.status == HoldStatus.ACTIVE.value,
            )
        ).first()
        if existing_booking or existing_hold:
            raise AlreadyHolding("You already have a booking or a pending offer for this slot.")
        current_time = now or datetime.now(timezone.utc)
        booking = Booking(
            slot_id=slot.id,
            user_id=user_id,
            booked_at=current_time,
            status=BookingStatus.CONFIRMED.value,
            source=BookingSource.DIRECT.value,
            recovered_from_booking_id=None
        )
        db.add(booking)
        sync_slot_status(db, slot)
        notifications.notify_booking_confirmed(db, booking, slot, now=current_time)
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
        current_time = now or datetime.now(timezone.utc)
        sync_slot_status(db, slot)
        by_business = slot.owner_id == actor_id
        payment_ledger.refund_for_cancelled_booking(db, booking, slot, by_business=by_business, now=current_time)
        notifications.notify_booking_cancelled(db, booking, slot, reason, by_business=by_business, now=current_time)
        hold, earliest_candidate = offer_all_candidates(db, slot, current_time)
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
        sync_slot_status(db, slot)
        hold, _ = offer_all_candidates(db, slot, current_time)
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
        db.refresh(hold)
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
            payment_ledger.close_payments_for_hold(db, hold.id)
            sync_slot_status(db, slot)
            offer_all_candidates(db, slot, current_time)
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
        is_recovery = hold.kind == HoldKind.OFFER.value
        prev_booking = db.scalars(
            select(Booking)
            .where(
                Booking.slot_id == slot.id,
                Booking.status == BookingStatus.CANCELLED.value
            )
            .order_by(Booking.booked_at.desc())
        ).first() if is_recovery else None
        booking = Booking(
            slot_id=slot.id,
            user_id=user_id,
            booked_at=current_time,
            status=BookingStatus.CONFIRMED.value,
            source=BookingSource.RECOVERED.value if is_recovery else BookingSource.DIRECT.value,
            recovered_from_booking_id=prev_booking.id if prev_booking else None
        )
        db.add(booking)
        sync_slot_status(db, slot)
        notifications.notify_booking_confirmed(db, booking, slot, now=current_time)
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
        payment_ledger.close_payments_for_hold(db, hold.id)
        current_time = now or datetime.now(timezone.utc)
        sync_slot_status(db, slot)
        offer_all_candidates(db, slot, current_time)
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
        payment_ledger.close_payments_for_hold(db, hold.id)
        current_time = now or datetime.now(timezone.utc)
        if hold.kind == HoldKind.OFFER.value:
            notifications.notify_offer_expired(db, hold, slot, now=current_time)
        sync_slot_status(db, slot)
        offer_all_candidates(db, slot, current_time)
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
        has_bookings = _seat_counts(db, slot)[0] > 0
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
        for hold in db.scalars(select(Hold).where(Hold.slot_id == slot.id)).all():
            payment_ledger.close_payments_for_hold(db, hold.id)
        if has_bookings:
            # A started session with confirmed bookings is a completed appointment, not an empty slot.
            db.flush()
            _set_slot_status(slot, SlotStatus.BOOKED.value)
            db.commit()
            return False
        assert_transition("Slot", slot.status, SlotStatus.CANCELLED.value)
        slot.status = SlotStatus.CANCELLED.value
        logger.info("past_slot_cancelled slot_id=%s", slot.id)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
