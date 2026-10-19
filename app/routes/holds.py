from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_customer, get_current_user
from app.models import Hold, HoldStatus, User
from app.schemas import HoldResponse, HoldExpiryCheckResponse, BookingResponse
from app.services.allocation_service import accept_hold, decline_hold, expire_hold
from app.services.payment_gateways import payment_required
from app.services.state_machine import NotFoundError, OfferExpired, InvalidTransition

router = APIRouter(prefix="/holds", tags=["Holds"])

@router.post("/{hold_id}/accept", response_model=BookingResponse, status_code=status.HTTP_200_OK, summary="Accept an active hold")
def accept_hold_endpoint(
    hold_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
) -> BookingResponse:
    pending_hold = db.get(Hold, hold_id)
    if pending_hold is not None and pending_hold.user_id == current_user.id and payment_required(pending_hold.slot):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Payment is required to accept this offer. Start checkout via POST /api/v1/payments/checkout.",
        )
    try:
        booking = accept_hold(db=db, hold_id=hold_id, user_id=current_user.id)
        return BookingResponse.model_validate(booking)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (OfferExpired, InvalidTransition, ValueError, IntegrityError):
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> HoldExpiryCheckResponse:
    hold = db.scalars(select(Hold).where(Hold.id == hold_id)).first()
    if not hold:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Hold with id '{hold_id}' not found.")
    slot_owner_id = hold.slot.owner_id if hold.slot else None
    if current_user.id != hold.user_id and current_user.id != slot_owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to inspect this hold")
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
