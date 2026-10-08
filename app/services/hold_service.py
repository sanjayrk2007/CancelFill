from datetime import datetime, timezone
from typing import Tuple
from sqlalchemy.orm import Session
from app.models import Hold, HoldStatus
from app.services.allocation_service import expire_hold

def check_and_update_hold_expiry(db: Session, hold_id: str) -> Tuple[Hold, bool]:
    hold = db.query(Hold).filter(Hold.id == hold_id).first()
    if not hold:
        raise ValueError(f"Hold with id '{hold_id}' not found.")
    now = datetime.now(timezone.utc)
    expires_at = hold.expires_at if hold.expires_at.tzinfo else hold.expires_at.replace(tzinfo=timezone.utc)
    is_expired = now > expires_at
    if is_expired and hold.status == HoldStatus.ACTIVE.value:
        hold = expire_hold(db=db, hold_id=hold_id, now=now)
    return hold, is_expired
