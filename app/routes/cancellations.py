from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import CancellationResultResponse
from app.services.allocation_service import cancel_booking
from app.services.state_machine import NotFoundError, InvalidTransition

router = APIRouter(prefix="/bookings", tags=["Cancellations"])

@router.post("/{booking_id}/cancel", response_model=CancellationResultResponse, summary="Cancel booking and trigger waitlist candidate selection")
def cancel_booking_endpoint(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    try:
        return cancel_booking(db=db, booking_id=booking_id, actor=current_user)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (InvalidTransition, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
