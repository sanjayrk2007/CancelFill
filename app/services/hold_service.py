from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.models import Hold, HoldStatus, Slot, SlotStatus
from app.config import settings

def create_hold_for_candidate(
    db: Session,
    slot_id: str,
    user_id: str,
    duration_minutes: Optional[int] = None
) -> Hold:
    """
    Creates a temporary hold for a selected candidate on a slot.
    """
    if duration_minutes is None:
        duration_minutes = settings.DEFAULT_HOLD_DURATION_MINUTES

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=duration_minutes)

    hold = Hold(
        slot_id=slot_id,
        user_id=user_id,
        created_at=now,
        expires_at=expires_at,
        status=HoldStatus.ACTIVE.value
    )
    db.add(hold)

    # Update slot status to HELD
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if slot:
        slot.status = SlotStatus.HELD.value

    db.commit()
    db.refresh(hold)
    return hold

def check_and_update_hold_expiry(db: Session, hold_id: str) -> Tuple[Hold, bool]:
    """
    Evaluates whether a hold has expired based on current timestamp comparison.
    If current_time > expires_at:
        hold.status = EXPIRED
        slot.status = AVAILABLE

    TODO – Next Sprint:
    Replace on-demand timestamp checking with a background scheduler (e.g. APScheduler/Celery)
    for automatic background expiry enforcement and cascading offers.
    """
    hold = db.query(Hold).filter(Hold.id == hold_id).first()
    if not hold:
        raise ValueError(f"Hold with id '{hold_id}' not found.")

    now = datetime.now(timezone.utc)

    # Ensure expires_at is timezone-aware for comparison
    expires_at = hold.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    is_expired = now > expires_at

    if is_expired and hold.status == HoldStatus.ACTIVE.value:
        hold.status = HoldStatus.EXPIRED.value
        
        # Release the slot back to AVAILABLE state
        slot = db.query(Slot).filter(Slot.id == hold.slot_id).first()
        if slot and slot.status == SlotStatus.HELD.value:
            slot.status = SlotStatus.AVAILABLE.value

        db.commit()
        db.refresh(hold)

    return hold, is_expired
