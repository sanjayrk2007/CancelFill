from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_customer
from app.models import Booking, BookingStatus, Hold, HoldStatus, User, WaitlistEntry, WaitlistStatus
from app.schemas import MyBookingResponse, MyOfferResponse, MyWaitlistEntryResponse, SlotResponse
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