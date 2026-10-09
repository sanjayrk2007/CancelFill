from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_customer
from app.models import (
    Booking, BookingSource, BookingStatus, Hold, HoldStatus, Slot, User, WaitlistEntry, WaitlistStatus
)
from app.schemas import CustomerStatsResponse, MyBookingResponse, MyOfferResponse, MyWaitlistEntryResponse, SlotResponse
from app.services.allocation_service import expire_hold


router = APIRouter(prefix="/me", tags=["Me"])


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@router.get("/offers", response_model=List[MyOfferResponse], summary="List my active offers")
def my_offers(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
    now: Optional[datetime] = None,
) -> List[MyOfferResponse]:
    current_time = now or datetime.now(timezone.utc)
    overdue_holds = list(
        db.scalars(
            select(Hold).where(
                Hold.user_id == current_user.id,
                Hold.status == HoldStatus.ACTIVE.value,
                Hold.expires_at <= current_time,
            )
        ).all()
    )
    for hold in overdue_holds:
        expire_hold(db=db, hold_id=hold.id, now=current_time)

    active_holds = list(
        db.scalars(
            select(Hold).where(
                Hold.user_id == current_user.id,
                Hold.status == HoldStatus.ACTIVE.value,
            ).order_by(Hold.expires_at.asc(), Hold.id.asc())
        ).all()
    )
    responses: List[MyOfferResponse] = []
    for hold in active_holds:
        seconds_remaining = max(0, int((_aware(hold.expires_at) - current_time).total_seconds()))
        responses.append(
            MyOfferResponse(
                id=hold.id,
                slot_id=hold.slot_id,
                user_id=hold.user_id,
                created_at=hold.created_at,
                expires_at=hold.expires_at,
                status=hold.status,
                slot=SlotResponse.model_validate(hold.slot),
                seconds_remaining=seconds_remaining,
            )
        )
    return responses


@router.get("/bookings", response_model=List[MyBookingResponse], summary="List my bookings")
def my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
) -> List[MyBookingResponse]:
    bookings = list(
        db.scalars(
            select(Booking).where(Booking.user_id == current_user.id).order_by(Booking.booked_at.desc(), Booking.id.asc())
        ).all()
    )
    return [
        MyBookingResponse(
            id=booking.id,
            slot_id=booking.slot_id,
            user_id=booking.user_id,
            booked_at=booking.booked_at,
            status=booking.status,
            source=booking.source,
            recovered_from_booking_id=booking.recovered_from_booking_id,
            slot=SlotResponse.model_validate(booking.slot),
        )
        for booking in bookings
    ]


@router.get("/waitlist", response_model=List[MyWaitlistEntryResponse], summary="List my waitlist entries")
def my_waitlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
) -> List[MyWaitlistEntryResponse]:
    entries = list(
        db.scalars(
            select(WaitlistEntry)
            .where(WaitlistEntry.user_id == current_user.id)
            .order_by(WaitlistEntry.joined_at.asc(), WaitlistEntry.id.asc())
        ).all()
    )
    responses: List[MyWaitlistEntryResponse] = []
    for entry in entries:
        position: Optional[int] = None
        if entry.status == WaitlistStatus.WAITING.value:
            waiting_entries = list(
                db.scalars(
                    select(WaitlistEntry)
                    .where(
                        WaitlistEntry.slot_id == entry.slot_id,
                        WaitlistEntry.status == WaitlistStatus.WAITING.value,
                    )
                    .order_by(WaitlistEntry.joined_at.asc(), WaitlistEntry.id.asc())
                ).all()
            )
            for idx, waiting_entry in enumerate(waiting_entries, start=1):
                if waiting_entry.id == entry.id:
                    position = idx
                    break
        responses.append(
            MyWaitlistEntryResponse(
                id=entry.id,
                slot_id=entry.slot_id,
                user_id=entry.user_id,
                joined_at=entry.joined_at,
                status=entry.status,
                priority_order=position,
                slot=SlotResponse.model_validate(entry.slot),
            )
        )
    return responses
@router.get("/stats", response_model=CustomerStatsResponse, summary="My activity summary")
def my_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
) -> CustomerStatsResponse:
    now = datetime.now(timezone.utc)

    booking_counts = dict(
        db.execute(
            select(Booking.status, func.count(Booking.id))
            .where(Booking.user_id == current_user.id)
            .group_by(Booking.status)
        ).all()
    )
    confirmed = int(booking_counts.get(BookingStatus.CONFIRMED.value, 0))
    cancelled = int(booking_counts.get(BookingStatus.CANCELLED.value, 0))

    upcoming = db.scalar(
        select(func.count(Booking.id))
        .join(Slot, Slot.id == Booking.slot_id)
        .where(
            Booking.user_id == current_user.id,
            Booking.status == BookingStatus.CONFIRMED.value,
            Slot.start_time > now,
        )
    ) or 0

    recovered = db.scalar(
        select(func.count(Booking.id)).where(
            Booking.user_id == current_user.id,
            Booking.status == BookingStatus.CONFIRMED.value,
            Booking.source == BookingSource.RECOVERED.value,
        )
    ) or 0

    hold_counts = dict(
        db.execute(
            select(Hold.status, func.count(Hold.id))
            .where(Hold.user_id == current_user.id)
            .group_by(Hold.status)
        ).all()
    )
    offers_received = int(sum(hold_counts.values()))
    accepted = int(hold_counts.get(HoldStatus.CONFIRMED.value, 0))
    declined = int(hold_counts.get(HoldStatus.DECLINED.value, 0))
    expired = int(hold_counts.get(HoldStatus.EXPIRED.value, 0))

    active_waitlist = db.scalar(
        select(func.count(WaitlistEntry.id)).where(
            WaitlistEntry.user_id == current_user.id,
            WaitlistEntry.status.in_([WaitlistStatus.WAITING.value, WaitlistStatus.OFFERED.value]),
        )
    ) or 0

    return CustomerStatsResponse(
        total_bookings=confirmed + cancelled,
        upcoming_bookings=int(upcoming),
        recovered_bookings=int(recovered),
        cancelled_bookings=cancelled,
        offers_received=offers_received,
        offers_accepted=accepted,
        offers_declined=declined,
        offers_expired=expired,
        acceptance_rate=(accepted / offers_received) if offers_received else 0.0,
        active_waitlist_entries=int(active_waitlist),
    )