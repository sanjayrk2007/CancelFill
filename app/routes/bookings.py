from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_customer
from app.models import Booking, User
from app.schemas import BookingCreate, BookingResponse
from app.models import Slot
from app.services.allocation_service import AlreadyHolding, book_slot
from app.services.payment_gateways import payment_required
from app.services.state_machine import NotFoundError, InvalidTransition

router = APIRouter(prefix="/bookings", tags=["Bookings"])

@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED, summary="Create a booking")
def create_booking(
    booking_in: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
) -> Booking:
    slot = db.get(Slot, booking_in.slot_id)
    if slot is not None and payment_required(slot):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Payment is required for this slot. Start checkout via POST /api/v1/payments/checkout.",
        )
    try:
        return book_slot(db=db, slot_id=booking_in.slot_id, user_id=current_user.id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AlreadyHolding as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except (InvalidTransition, ValueError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This offer is no longer available"
        )
