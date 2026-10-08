from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_customer
from app.models import Booking, User
from app.schemas import BookingCreate, BookingResponse
from app.services.allocation_service import book_slot
from app.services.state_machine import NotFoundError, InvalidTransition

router = APIRouter(prefix="/bookings", tags=["Bookings"])

@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED, summary="Create a booking")
def create_booking(
    booking_in: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
) -> Booking:
    try:
        return book_slot(db=db, slot_id=booking_in.slot_id, user_id=current_user.id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (InvalidTransition, ValueError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This offer is no longer available"
        )
