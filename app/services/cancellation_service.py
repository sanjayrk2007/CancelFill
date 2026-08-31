from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import Booking, BookingStatus, Slot, SlotStatus, WaitlistEntry, WaitlistStatus
from app.services.waitlist_service import get_waitlist_for_slot
from app.services.hold_service import create_hold_for_candidate

def process_cancellation(db: Session, booking_id: str) -> Dict[str, Any]:
    """
    First-pass cancellation and candidate-selection workflow.
    
    1. Mark booking.status = CANCELLED
    2. Set slot.status = AVAILABLE
    3. Check waitlist for slot ordered by joined_at ASC
    4. Select earliest eligible candidate
    5. Mark waitlist entry status = OFFERED
    6. Create temporary hold for candidate (slot.status = HELD)
    
    TODO – Next Sprint:
    Implement SELECT FOR UPDATE / row locking to prevent race conditions during concurrent cancellations.
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise ValueError(f"Booking with id '{booking_id}' not found.")

    if booking.status == BookingStatus.CANCELLED.value:
        raise ValueError(f"Booking '{booking_id}' is already cancelled.")

    # Step 1: Mark booking as CANCELLED
    booking.status = BookingStatus.CANCELLED.value
    slot = db.query(Slot).filter(Slot.id == booking.slot_id).first()
    
    if not slot:
        raise ValueError(f"Associated slot '{booking.slot_id}' not found.")

    # Step 2: Temporarily set slot status to AVAILABLE prior to checking waitlist
    slot.status = SlotStatus.AVAILABLE.value
    db.commit()

    # Step 3: Query active waitlist candidates ordered by joined_at ASC
    candidates = get_waitlist_for_slot(db, slot_id=slot.id)

    if candidates:
        # Step 4: Select earliest candidate (first in ordered list)
        earliest_candidate = candidates[0]
        
        # Step 5: Mark candidate status as OFFERED
        earliest_candidate.status = WaitlistStatus.OFFERED.value
        db.commit()

        # Step 6: Create temporary hold (updates slot.status to HELD)
        hold = create_hold_for_candidate(
            db=db,
            slot_id=slot.id,
            user_id=earliest_candidate.user_id
        )

        return {
            "booking_id": booking.id,
            "booking_status": booking.status,
            "slot_id": slot.id,
            "slot_status": slot.status,
            "candidate_selected": True,
            "selected_user_id": earliest_candidate.user_id,
            "hold": hold,
            "message": f"Booking cancelled. Slot recovered and offered to earliest candidate '{earliest_candidate.user_id}' with temporary hold."
        }
    else:
        db.commit()
        return {
            "booking_id": booking.id,
            "booking_status": booking.status,
            "slot_id": slot.id,
            "slot_status": slot.status,
            "candidate_selected": False,
            "selected_user_id": None,
            "hold": None,
            "message": "Booking cancelled. No waitlist candidates found; slot is now AVAILABLE."
        }
