from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import CancellationResultResponse
from app.services.cancellation_service import process_cancellation

router = APIRouter(prefix="/bookings", tags=["Cancellations"])

@router.post("/{booking_id}/cancel", response_model=CancellationResultResponse, summary="Cancel booking and trigger waitlist candidate selection")
def cancel_booking_endpoint(booking_id: str, db: Session = Depends(get_db)):
    """
    Cancels an existing booking, releases the slot, evaluates waitlist entries by priority (earliest joined_at),
    and creates a temporary hold for the highest-priority candidate.
    """
    try:
        result = process_cancellation(db=db, booking_id=booking_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
