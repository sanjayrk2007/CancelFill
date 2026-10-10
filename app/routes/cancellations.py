from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import CancelBookingRequest, CancellationResultResponse
from app.services.allocation_service import cancel_booking
from app.services.state_machine import NotFoundError, InvalidTransition, ReasonRequired

router = APIRouter(prefix="/bookings", tags=["Cancellations"])

@router.post("/{booking_id}/cancel", response_model=CancellationResultResponse, summary="Cancel booking and trigger waitlist candidate selection")
def cancel_booking_endpoint(
    booking_id: str,
    body: Optional[CancelBookingRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    reason = (body.reason if body else None) or None
    try:
        return cancel_booking(db=db, booking_id=booking_id, actor=current_user, reason=reason)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ReasonRequired as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except (InvalidTransition, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
