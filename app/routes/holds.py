from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_customer
from app.models import Hold, HoldStatus, User
from app.schemas import HoldResponse, HoldExpiryCheckResponse, BookingResponse
from app.services.allocation_service import accept_hold, decline_hold, expire_hold
from app.services.state_machine import NotFoundError, OfferExpired, InvalidTransition

router = APIRouter(prefix="/holds", tags=["Holds"])

@router.get("", response_model=List[HoldResponse], summary="List all holds")
def list_holds(db: Session = Depends(get_db)) -> List[Hold]:
    return list(db.scalars(select(Hold)).all())

@router.post("/{hold_id}/accept", response_model=BookingResponse, status_code=status.HTTP_200_OK, summary="Accept an active hold")
def accept_hold_endpoint(
    hold_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
) -> BookingResponse:
    try:
        booking = accept_hold(db=db, hold_id=hold_id, user_id=current_user.id)
        return BookingResponse.model_validate(booking)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (OfferExpired, InvalidTransition, ValueError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This offer is no longer available")

@router.post("/{hold_id}/decline", response_model=HoldResponse, status_code=status.HTTP_200_OK, summary="Decline an active hold")
def decline_hold_endpoint(
    hold_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
) -> HoldResponse:
    try:
        hold = decline_hold(db=db, hold_id=hold_id, user_id=current_user.id)
        return HoldResponse.model_validate(hold)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (InvalidTransition, ValueError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This offer is no longer available")

@router.post("/{hold_id}/check-expiry", response_model=HoldExpiryCheckResponse, summary="Check and evaluate timestamp-based hold expiry")
def check_hold_expiry_endpoint(
    hold_id: str,
    db: Session = Depends(get_db)
) -> HoldExpiryCheckResponse:
    hold = db.scalars(select(Hold).where(Hold.id == hold_id)).first()
    if not hold:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Hold with id '{hold_id}' not found.")
    now = datetime.now(timezone.utc)
    expires_at = hold.expires_at if hold.expires_at.tzinfo else hold.expires_at.replace(tzinfo=timezone.utc)
    is_expired = now > expires_at
    if is_expired and hold.status == HoldStatus.ACTIVE.value:
        hold = expire_hold(db=db, hold_id=hold_id, now=now)
    msg = "Hold is EXPIRED. Slot released back to AVAILABLE status." if is_expired else "Hold is currently ACTIVE."
    slot_status = hold.slot.status if hold.slot else "UNKNOWN"
    return HoldExpiryCheckResponse(
        hold_id=hold.id,
        status=hold.status,
        is_expired=is_expired,
        expires_at=hold.expires_at,
        checked_at=now,
        slot_id=hold.slot_id,
        slot_status=slot_status,
        message=msg
    )
