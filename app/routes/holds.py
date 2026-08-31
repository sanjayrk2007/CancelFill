from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Hold
from app.schemas import HoldResponse, HoldExpiryCheckResponse
from app.services.hold_service import check_and_update_hold_expiry

router = APIRouter(prefix="/holds", tags=["Holds"])

@router.get("", response_model=List[HoldResponse], summary="List all holds")
def list_holds(db: Session = Depends(get_db)):
    """
    Returns all temporary holds in the system.
    """
    return db.query(Hold).all()

@router.post("/{hold_id}/check-expiry", response_model=HoldExpiryCheckResponse, summary="Check and evaluate timestamp-based hold expiry")
def check_hold_expiry_endpoint(hold_id: str, db: Session = Depends(get_db)):
    """
    Evaluates whether current_time > expires_at for a given hold.
    If expired, hold status becomes EXPIRED and slot status becomes AVAILABLE.
    
    TODO – Next Sprint:
    Replace on-demand API check with a background scheduler worker.
    """
    try:
        hold, is_expired = check_and_update_hold_expiry(db=db, hold_id=hold_id)
        now = datetime.now(timezone.utc)
        
        msg = "Hold is EXPIRED. Slot released back to AVAILABLE status." if is_expired else "Hold is currently ACTIVE."
        
        return HoldExpiryCheckResponse(
            hold_id=hold.id,
            status=hold.status,
            is_expired=is_expired,
            expires_at=hold.expires_at,
            checked_at=now,
            slot_id=hold.slot_id,
            slot_status=hold.slot.status if hold.slot else "UNKNOWN",
            message=msg
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
