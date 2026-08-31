from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Booking, BookingStatus, Slot, SlotStatus
from app.schemas import BookingCreate, BookingResponse

router = APIRouter(prefix="/bookings", tags=["Bookings"])

@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED, summary="Create a booking (minimal setup for demo)")
def create_booking(booking_in: BookingCreate, db: Session = Depends(get_db)):
    """
    Creates an initial booking on a slot to enable testing the cancellation flow.
    """
    slot = db.query(Slot).filter(Slot.id == booking_in.slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail=f"Slot '{booking_in.slot_id}' not found.")

    if slot.status != SlotStatus.AVAILABLE.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot book slot '{booking_in.slot_id}': current status is '{slot.status}'."
        )

    booking = Booking(
        slot_id=booking_in.slot_id,
        user_id=booking_in.user_id,
        booked_at=datetime.now(timezone.utc),
        status=BookingStatus.CONFIRMED.value
    )
    slot.status = SlotStatus.BOOKED.value
    
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking

@router.get("", response_model=List[BookingResponse], summary="List all bookings")
def list_bookings(db: Session = Depends(get_db)):
    """
    Lists all bookings in the system.
    """
    return db.query(Booking).all()
