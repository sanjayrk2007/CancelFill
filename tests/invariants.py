from sqlalchemy.orm import Session

from app.models import Booking, BookingStatus, Hold, HoldStatus, Slot, SlotStatus


def assert_invariants(db: Session) -> None:
    """Assert the slot/child state invariants that must hold after allocation races."""
    db.expire_all()
    slots = db.query(Slot).all()
    for slot in slots:
        active_holds = db.query(Hold).filter(
            Hold.slot_id == slot.id,
            Hold.status == HoldStatus.ACTIVE.value,
        ).all()
        confirmed_bookings = db.query(Booking).filter(
            Booking.slot_id == slot.id,
            Booking.status == BookingStatus.CONFIRMED.value,
        ).all()

        assert len(active_holds) <= 1, f"slot {slot.id} has multiple ACTIVE holds"
        assert len(confirmed_bookings) <= 1, f"slot {slot.id} has multiple CONFIRMED bookings"
        assert not (active_holds and confirmed_bookings), (
            f"slot {slot.id} cannot have both an ACTIVE hold and a CONFIRMED booking"
        )

        if active_holds:
            assert slot.status == SlotStatus.HELD.value, (
                f"slot {slot.id} has an ACTIVE hold but status is {slot.status}"
            )
        elif confirmed_bookings:
            assert slot.status == SlotStatus.BOOKED.value, (
                f"slot {slot.id} has a CONFIRMED booking but status is {slot.status}"
            )
        else:
            assert slot.status == SlotStatus.AVAILABLE.value, (
                f"slot {slot.id} has no ACTIVE hold/CONFIRMED booking but status is {slot.status}"
            )