from decimal import Decimal
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session, aliased

from app.database import get_db
from app.dependencies import require_business
from app.models import Booking, BookingSource, BookingStatus, Hold, HoldStatus, Slot, User, WaitlistEntry, WaitlistStatus
from app.schemas import (
    BusinessBookingResponse,
    BusinessSlotResponse,
    BusinessStatsResponse,
    BusinessWaitlistEntryResponse,
    BusinessWaitlistSlotResponse,
)


router = APIRouter(prefix="/business", tags=["Business"])


@router.get("/stats", response_model=BusinessStatsResponse, summary="Business recovery statistics")
def business_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_business),
) -> BusinessStatsResponse:
    slot_stats = db.execute(
        select(
            func.count(Slot.id).label("total_slots"),
            func.coalesce(func.sum(case((Slot.status == "BOOKED", 1), else_=0)), 0).label("booked_slots"),
        ).where(Slot.owner_id == current_user.id)
    ).one()

    booking_stats = db.execute(
        select(
            func.coalesce(func.sum(case((Booking.status == BookingStatus.CANCELLED.value, 1), else_=0)), 0).label("cancellations"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Booking.status == BookingStatus.CONFIRMED.value,
                                Booking.source == BookingSource.RECOVERED.value,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("recovered_bookings"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Booking.status == BookingStatus.CONFIRMED.value,
                                Booking.source == BookingSource.RECOVERED.value,
                            ),
                            Slot.price,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("recovered_revenue"),
        )
        .select_from(Booking)
        .join(Slot, Slot.id == Booking.slot_id)
        .where(Slot.owner_id == current_user.id)
    ).one()

    offer_stats = db.execute(
        select(
            func.count(Hold.id).label("offers_made"),
            func.coalesce(func.sum(case((Hold.status == HoldStatus.CONFIRMED.value, 1), else_=0)), 0).label("offers_accepted"),
            func.coalesce(func.sum(case((Hold.status == HoldStatus.DECLINED.value, 1), else_=0)), 0).label("offers_declined"),
            func.coalesce(func.sum(case((Hold.status == HoldStatus.EXPIRED.value, 1), else_=0)), 0).label("offers_expired"),
        )
        .select_from(Hold)
        .join(Slot, Slot.id == Hold.slot_id)
        .where(Slot.owner_id == current_user.id)
    ).one()

    total_slots = int(slot_stats.total_slots or 0)
    booked_slots = int(slot_stats.booked_slots or 0)
    offers_made = int(offer_stats.offers_made or 0)
    offers_accepted = int(offer_stats.offers_accepted or 0)
    recovered_revenue = Decimal(booking_stats.recovered_revenue or 0).quantize(Decimal("0.01"))
    return BusinessStatsResponse(
        total_slots=total_slots,
        booked_slots=booked_slots,
        utilization_rate=(booked_slots / total_slots) if total_slots else 0,
        cancellations=int(booking_stats.cancellations or 0),
        offers_made=offers_made,
        offers_accepted=offers_accepted,
        offers_declined=int(offer_stats.offers_declined or 0),
        offers_expired=int(offer_stats.offers_expired or 0),
        conversion_rate=(offers_accepted / offers_made) if offers_made else 0,
        recovered_bookings=int(booking_stats.recovered_bookings or 0),
        recovered_revenue=recovered_revenue,
    )


@router.get("/slots", response_model=List[BusinessSlotResponse], summary="Business owned slot dashboard")
def business_slots(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_business),
) -> List[BusinessSlotResponse]:
    booking_holder = aliased(User)
    hold_holder = aliased(User)
    waitlist_counts = (
        select(WaitlistEntry.slot_id, func.count(WaitlistEntry.id).label("waitlist_count"))
        .where(WaitlistEntry.status.in_([WaitlistStatus.WAITING.value, WaitlistStatus.OFFERED.value]))
        .group_by(WaitlistEntry.slot_id)
        .subquery()
    )
    active_bookings = (
        select(Booking.id.label("booking_id"), Booking.slot_id, Booking.user_id)
        .where(Booking.status == BookingStatus.CONFIRMED.value)
        .subquery()
    )
    active_holds = (
        select(Hold.slot_id, Hold.user_id, Hold.expires_at)
        .where(Hold.status == HoldStatus.ACTIVE.value)
        .subquery()
    )
    rows = db.execute(
        select(
            Slot.id,
            Slot.resource_id,
            Slot.start_time,
            Slot.end_time,
            Slot.status,
            Slot.price,
            func.coalesce(waitlist_counts.c.waitlist_count, 0).label("waitlist_count"),
            active_bookings.c.booking_id,
            booking_holder.name.label("booking_holder_name"),
            hold_holder.name.label("hold_holder_name"),
            active_holds.c.expires_at.label("hold_expires_at"),
        )
        .select_from(Slot)
        .outerjoin(waitlist_counts, waitlist_counts.c.slot_id == Slot.id)
        .outerjoin(active_bookings, active_bookings.c.slot_id == Slot.id)
        .outerjoin(booking_holder, booking_holder.id == active_bookings.c.user_id)
        .outerjoin(active_holds, active_holds.c.slot_id == Slot.id)
        .outerjoin(hold_holder, hold_holder.id == active_holds.c.user_id)
        .where(Slot.owner_id == current_user.id)
        .order_by(Slot.start_time.asc(), Slot.id.asc())
    ).all()
    return [
        BusinessSlotResponse(
            id=row.id,
            resource_id=row.resource_id,
            start_time=row.start_time,
            end_time=row.end_time,
            status=row.status,
            price=row.price,
            waitlist_count=int(row.waitlist_count or 0),
            active_booking_id=row.booking_id,
            active_booking_holder_name=row.booking_holder_name,
            active_hold_holder_name=row.hold_holder_name,
            active_hold_expires_at=row.hold_expires_at,
        )
        for row in rows
    ]


@router.get("/waitlist", response_model=List[BusinessWaitlistSlotResponse], summary="Business owned active waitlists")
def business_waitlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_business),
) -> List[BusinessWaitlistSlotResponse]:
    waiting_positions = (
        select(
            WaitlistEntry.id.label("entry_id"),
            func.row_number()
            .over(partition_by=WaitlistEntry.slot_id, order_by=(WaitlistEntry.joined_at.asc(), WaitlistEntry.id.asc()))
            .label("position"),
        )
        .where(WaitlistEntry.status == WaitlistStatus.WAITING.value)
        .subquery()
    )
    rows = db.execute(
        select(
            Slot.id.label("slot_id"),
            Slot.resource_id,
            WaitlistEntry.id.label("entry_id"),
            WaitlistEntry.user_id,
            User.name.label("user_name"),
            WaitlistEntry.joined_at,
            WaitlistEntry.status,
            waiting_positions.c.position,
        )
        .select_from(WaitlistEntry)
        .join(Slot, Slot.id == WaitlistEntry.slot_id)
        .join(User, User.id == WaitlistEntry.user_id)
        .outerjoin(waiting_positions, waiting_positions.c.entry_id == WaitlistEntry.id)
        .where(
            Slot.owner_id == current_user.id,
            WaitlistEntry.status.in_([WaitlistStatus.WAITING.value, WaitlistStatus.OFFERED.value]),
        )
        .order_by(Slot.start_time.asc(), Slot.id.asc(), WaitlistEntry.joined_at.asc(), WaitlistEntry.id.asc())
    ).all()

    grouped: Dict[str, BusinessWaitlistSlotResponse] = {}
    for row in rows:
        if row.slot_id not in grouped:
            grouped[row.slot_id] = BusinessWaitlistSlotResponse(slot_id=row.slot_id, resource_id=row.resource_id, entries=[])
        grouped[row.slot_id].entries.append(
            BusinessWaitlistEntryResponse(
                id=row.entry_id,
                user_id=row.user_id,
                user_name=row.user_name,
                joined_at=row.joined_at,
                status=row.status,
                position=int(row.position) if row.position is not None else None,
            )
        )
    return list(grouped.values())


@router.get("/bookings", response_model=List[BusinessBookingResponse], summary="Business owned bookings")
def business_bookings(
    status: Optional[BookingStatus] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_business),
) -> List[BusinessBookingResponse]:
    query = (
        select(
            Booking.id,
            Booking.slot_id,
            Booking.user_id,
            User.name.label("holder_name"),
            Booking.booked_at,
            Booking.status,
            Booking.source,
            Booking.recovered_from_booking_id,
            Slot.price.label("slot_price"),
        )
        .select_from(Booking)
        .join(Slot, Slot.id == Booking.slot_id)
        .join(User, User.id == Booking.user_id)
        .where(Slot.owner_id == current_user.id)
        .order_by(Booking.booked_at.desc(), Booking.id.asc())
    )
    if status is not None:
        query = query.where(Booking.status == status.value)
    rows = db.execute(query).all()
    return [
        BusinessBookingResponse(
            id=row.id,
            slot_id=row.slot_id,
            user_id=row.user_id,
            holder_name=row.holder_name,
            booked_at=row.booked_at,
            status=row.status,
            source=row.source,
            recovered_from_booking_id=row.recovered_from_booking_id,
            slot_price=row.slot_price,
        )
        for row in rows
    ]